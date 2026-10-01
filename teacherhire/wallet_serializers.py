from rest_framework import serializers
from .models import Wallet, WalletTransaction, PointConfiguration, PaymentTransaction

class WalletTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletTransaction
        fields = ['id', 'amount', 'transaction_type', 'reference', 'status', 'description', 'created_at']

class WalletSerializer(serializers.ModelSerializer):
    transactions = WalletTransactionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Wallet
        fields = ['balance', 'transactions']
        
class PointConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PointConfiguration
        fields = ['point_price_in_inr']
