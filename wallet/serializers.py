from rest_framework import serializers
from wallet.models import Wallet

class WalletsSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Wallet
        fields = ['url', 'id']

class WalletSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Wallet
        fields = ['balance']  

class WalletOperationSerializer(serializers.Serializer):
    operation_type = serializers.ChoiceField(choices=['DEPOSIT', 'WITHDRAW'], 
                                             required=True
    )
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, 
                                      required=True
    )

    def validate(self, data):
        wallet = self.context['wallet']
        if (data['operation_type'] == 'WITHDRAW' 
            and data['amount'] > wallet.balance
            ):
            raise serializers.ValidationError({
                "amount": "Недостаточно средств на счете"
            })
        return data