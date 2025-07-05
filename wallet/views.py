from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from wallet.models import Wallet
from wallet.serializers import (WalletsSerializer, 
                                WalletSerializer, 
                                WalletOperationSerializer,
)

class WalletsViewSet(viewsets.ModelViewSet):
    queryset = Wallet.objects.all()
    serializer_class = WalletsSerializer
    def get_serializer_class(self):
        if self.action == 'list':
            return WalletsSerializer
        elif self.action == 'retrieve':
            return WalletSerializer
        return super().get_serializer_class()   
    
    def create(self, request):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)


    @action(detail=True, methods=['post'])
    def operation(self, request, pk):
        wallet = get_object_or_404(Wallet, pk=pk)
        serializer = WalletOperationSerializer(data=request.data)
        if serializer.is_valid():
            operation_type = serializer.validated_data['operation_type']
            amount = serializer.validated_data['amount']
            if operation_type == 'DEPOSIT':
                wallet.balance += amount
            elif operation_type == 'WITHDRAW':
                wallet.balance -= amount
            wallet.save()
            wallet_serializer = WalletSerializer(wallet)
            return Response(wallet_serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
