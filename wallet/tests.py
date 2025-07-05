from unittest.mock import patch

from decimal import Decimal
from django.test import TestCase, Client
from django.core.exceptions import ValidationError
from wallet.models import Wallet
from wallet.views import WalletsViewSet
from rest_framework.decorators import permission_classes
from rest_framework.permissions import AllowAny

# Тестирование модели Wallet
class WalletModelTest(TestCase):
    def test_wallet_balance_negative(self):
        balance = "-100"
        wallet = Wallet(balance=balance)
        with self.assertRaises(expected_exception=ValidationError):
            wallet.full_clean()
        
    def test_wallet_balance_zero(self):
        balance = "0"
        wallet = Wallet(balance=balance)
        self.assertIsNone(wallet.full_clean())
    
    def test_wallet_balance_positive(self):
        balance = "1000"
        wallet = Wallet(balance=balance)
        self.assertIsNone(wallet.full_clean())
    
    def test_wallet_decimal_more_than_2(self):
        balance = Decimal("10.123")
        wallet = Wallet(balance=balance)
        with self.assertRaises(expected_exception=ValidationError):
            wallet.full_clean()

    def test_wallet_decimal_less_eq_2(self):
        balance = Decimal("10.12")
        wallet = Wallet(balance=balance)
        balance1 = Decimal("10.1")
        wallet1 = Wallet(balance=balance1)
        self.assertIsNone(wallet.full_clean())
        self.assertIsNone(wallet1.full_clean())

    def test_wallet_digits_more_than_10(self):
        balance = "12345678901.12"
        wallet = Wallet(balance=balance)
        with self.assertRaises(expected_exception=ValidationError):
            wallet.full_clean()
    
    def test_wallet_digits_less_eq_10(self):
        balance = "1234567890"
        wallet = Wallet(balance=balance)
        balance1 = "12345678.12"
        wallet1 = Wallet(balance=balance1)
        self.assertIsNone(wallet.full_clean())
        self.assertIsNone(wallet1.full_clean())

    def test_wallet_unique_create(self):
        wallet = Wallet(balance=0)
        wallet.save()
        wallet1 = Wallet(balance=0)        
        wallet1.save()
        self.assertNotEqual(wallet.id, wallet1.id)

# тестирование вьюхи
class WalletsViewSetTest(TestCase):
    def setup(self):
        self.client = Client()

    def test_wallets_request_GET(self):
        response = self.client.get('/api/v1/wallets/', 
                                   content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)

    # убрал проверку на авторизацию для теста, иначе выдаёт 403
    def test_wallets_request_POST(self):
        with patch(
            'wallet.views.WalletsViewSet.permission_classes', [AllowAny]
        ):
            response = self.client.post('/api/v1/wallets/', 
                                        content_type='application/json'
            )
            self.assertEqual(response.status_code, 405)
    
    def test_uuid_request_GET(self):
        wallet = Wallet(balance=0)
        wallet.save()
        response = self.client.get(f'/api/v1/wallets/{wallet.id}/', 
                                   content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)

    def test_uuid_request_POST(self):
        wallet = Wallet(balance=0)
        wallet.save()
        with patch(
            'wallet.views.WalletsViewSet.permission_classes', [AllowAny]
        ):
            response = self.client.post(f'/api/v1/wallets/{wallet.id}/', 
                                        content_type='application/json'
            )
            self.assertEqual(response.status_code, 405)

    def test_operation_request_GET(self):
        wallet = Wallet(balance=0)
        wallet.save()
        response = self.client.get(f'/api/v1/wallets/{wallet.id}/operation/', 
                                   content_type='application/json'
        )
        self.assertEqual(response.status_code, 405)
    
    def test_operation_request_POST(self):
        wallet = Wallet(balance=0)
        wallet.save()
        with patch(
            'wallet.views.WalletsViewSet.permission_classes', [AllowAny]
        ):
            response = self.client.post(
                f'/api/v1/wallets/{wallet.id}/operation/',
                data={'operation_type':'DEPOSIT',
                      'amount':'100'
                },
                content_type='application/json', 
            )
            self.assertEqual(response.status_code, 200)
    
    def test_operation_WITHDRAW_subzero(self):
        wallet = Wallet(balance=0)
        wallet.save()
        with patch(
            'wallet.views.WalletsViewSet.permission_classes', [AllowAny]
        ):
            response = self.client.post(
                f'/api/v1/wallets/{wallet.id}/operation/',
                data={'operation_type':'WITHDRAW',
                      'amount':'0.20'
                },
                content_type='application/json', 
            )
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json(), 
                             {'amount': ['Недостаточно средств на счете']
            })

    def test_operation_WITHDRAW(self):
        wallet = Wallet(balance=1000)
        wallet.save()
        with patch(
            'wallet.views.WalletsViewSet.permission_classes', [AllowAny]
        ):
            response = self.client.post(
                f'/api/v1/wallets/{wallet.id}/operation/',
                data={'operation_type':'WITHDRAW',
                      'amount':'200.20'
                },
                content_type='application/json', 
            )
            self.assertEqual(response.status_code, 200)
            wallet.refresh_from_db()
            self.assertEqual(wallet.balance, Decimal('799.80'))   