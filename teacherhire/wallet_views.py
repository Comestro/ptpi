import razorpay
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Wallet, PointConfiguration, PaymentTransaction, WalletTransaction
from .wallet_serializers import WalletSerializer, PointConfigurationSerializer
from decimal import Decimal

# Initialize Razorpay client
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

class WalletDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wallet, created = Wallet.objects.get_or_create(user=request.user)
        # Give welcome points if created and available
        if created:
            config = PointConfiguration.objects.first()
            if config and config.welcome_points > 0:
                wallet.balance = config.welcome_points
                wallet.save()
                WalletTransaction.objects.create(
                    wallet=wallet,
                    amount=config.welcome_points,
                    transaction_type='CREDIT',
                    description="Welcome Points Bonus"
                )
        
        serializer = WalletSerializer(wallet)
        
        # Add config to response
        config = PointConfiguration.objects.first()
        config_data = PointConfigurationSerializer(config).data if config else {"point_price_in_inr": 1.0}
        
        return Response({"wallet": serializer.data, "config": config_data}, status=200)


class CreatePaymentOrderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        points_to_buy = request.data.get('points')
        if not points_to_buy or int(points_to_buy) <= 0:
            return Response({"error": "Invalid points amount"}, status=400)
            
        points_to_buy = int(points_to_buy)
        config = PointConfiguration.objects.first()
        price_per_point = config.point_price_in_inr if config else Decimal('1.00')
        
        amount_in_inr = Decimal(points_to_buy) * price_per_point
        amount_in_paise = int(amount_in_inr * 100)
        
        # Create Razorpay order
        try:
            order_data = {
                'amount': amount_in_paise,
                'currency': 'INR',
                'receipt': f'user_{request.user.id}_points_{points_to_buy}'
            }
            razorpay_order = razorpay_client.order.create(data=order_data)
            
            # Save transaction in db as PENDING
            PaymentTransaction.objects.create(
                user=request.user,
                amount_paid=amount_in_inr,
                points_purchased=points_to_buy,
                razorpay_order_id=razorpay_order['id'],
                payment_status='PENDING'
            )
            
            return Response({
                "order_id": razorpay_order['id'],
                "amount": amount_in_paise,
                "currency": "INR",
                "key_id": settings.RAZORPAY_KEY_ID
            }, status=200)
            
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class VerifyPaymentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        razorpay_payment_id = request.data.get('razorpay_payment_id')
        razorpay_order_id = request.data.get('razorpay_order_id')
        razorpay_signature = request.data.get('razorpay_signature')

        try:
            # Verify signature
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            }
            razorpay_client.utility.verify_payment_signature(params_dict)
            
            from django.db import transaction
            
            with transaction.atomic():
                # Find the transaction and lock it
                payment_transaction = PaymentTransaction.objects.select_for_update().get(razorpay_order_id=razorpay_order_id, user=request.user)
                
                if payment_transaction.payment_status == 'SUCCESS':
                    return Response({"message": "Payment already verified"}, status=200)
                    
                # Update transaction
                payment_transaction.razorpay_payment_id = razorpay_payment_id
                payment_transaction.razorpay_signature = razorpay_signature
                payment_transaction.payment_status = 'SUCCESS'
                payment_transaction.save()
                
                # Add points to wallet
                wallet, _ = Wallet.objects.get_or_create(user=request.user)
                wallet = Wallet.objects.select_for_update().get(id=wallet.id)
                wallet.balance += payment_transaction.points_purchased
                wallet.save()
                
                # Log wallet transaction
                WalletTransaction.objects.create(
                    wallet=wallet,
                    amount=payment_transaction.points_purchased,
                    transaction_type='CREDIT',
                    reference=f"PAY_{razorpay_payment_id}",
                    description="Purchased points via Razorpay"
                )
                
                return Response({"message": "Payment successful. Points added to wallet.", "new_balance": wallet.balance}, status=200)
            
        except razorpay.errors.SignatureVerificationError:
            # Mark transaction as failed
            PaymentTransaction.objects.filter(razorpay_order_id=razorpay_order_id).update(payment_status='FAILED')
            return Response({"error": "Payment signature verification failed"}, status=400)
        except PaymentTransaction.DoesNotExist:
            return Response({"error": "Payment transaction not found"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

from rest_framework.permissions import AllowAny
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import hmac
import hashlib

@method_decorator(csrf_exempt, name='dispatch')
class RazorpayWebhookAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        webhook_signature = request.headers.get('X-Razorpay-Signature')
        if not webhook_signature:
            return Response({"error": "No signature"}, status=400)
            
        webhook_secret = settings.RAZORPAY_KEY_SECRET # or a specific webhook secret if set
        
        # Verify webhook signature manually
        try:
            expected_signature = hmac.new(
                webhook_secret.encode('utf-8'),
                request.body,
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(expected_signature, webhook_signature):
                return Response({"error": "Invalid signature"}, status=400)
        except Exception:
            return Response({"error": "Signature verification failed"}, status=400)
            
        payload = request.data
        event = payload.get('event')
        
        if event == 'payment.captured' or event == 'payment.authorized':
            payment = payload['payload']['payment']['entity']
            order_id = payment.get('order_id')
            payment_id = payment.get('id')
            
            if order_id:
                from django.db import transaction
                try:
                    with transaction.atomic():
                        payment_transaction = PaymentTransaction.objects.select_for_update().get(razorpay_order_id=order_id)
                        
                        if payment_transaction.payment_status != 'SUCCESS':
                            payment_transaction.razorpay_payment_id = payment_id
                            payment_transaction.payment_status = 'SUCCESS'
                            payment_transaction.save()
                            
                            wallet, _ = Wallet.objects.get_or_create(user=payment_transaction.user)
                            wallet = Wallet.objects.select_for_update().get(id=wallet.id)
                            wallet.balance += payment_transaction.points_purchased
                            wallet.save()
                            
                            WalletTransaction.objects.create(
                                wallet=wallet,
                                amount=payment_transaction.points_purchased,
                                transaction_type='CREDIT',
                                reference=f"PAY_WEBHOOK_{payment_id}",
                                description="Purchased points via Razorpay Webhook"
                            )
                except PaymentTransaction.DoesNotExist:
                    pass
                    
        return Response({"status": "ok"}, status=200)
