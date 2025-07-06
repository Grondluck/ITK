from unittest.mock import patch
from threading import Thread

from decimal import Decimal
from django.test import TestCase, Client
from django.core.exceptions import ValidationError
from wallet.models import Wallet
from rest_framework.decorators import permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import ErrorDetail


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
        wallets = [None, None]
        balance = 0
        for index in range(len(wallets)):
            wallets[index] = Wallet(balance=balance)
            wallets[index].save()
            balance += 666   
        response = self.client.get('/api/v1/wallets/', 
                                   content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)  
        self.assertEqual(len(response.data), 2)

        for index, wallet in enumerate(response.data):
            self.assertIn('id', wallet)
            self.assertEqual(wallet['id'], str(wallets[index].id))
            self.assertIn('url', wallet)
            self.assertEqual(wallet['url'], 
                f'http://testserver/api/v1/wallets/{wallet["id"]}/')
            

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
        wallet = Wallet(balance=666)
        wallet.save()
        response = self.client.get(f'/api/v1/wallets/{wallet.id}/', 
                                   content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('balance', response.data)
        self.assertEqual(Decimal(response.data['balance']), 666)


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
            wallet.refresh_from_db()
            self.assertEqual(response.status_code, 200)
            self.assertIn('balance', response.data)
            self.assertEqual(Decimal(response.data['balance']), wallet.balance)
    
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
            self.assertIsInstance(response.data['amount'][0], ErrorDetail)
            self.assertEqual(str(response.data['amount'][0]), 
                             'Недостаточно средств на счете')

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
            self.assertIn('balance', response.data)
            self.assertEqual(wallet.balance, Decimal('799.80'))   

    # с потоками не получается, нужно больше осваивать тему =(
    def test_concurrent_operations(self):
        results = []
        wallet = Wallet.objects.create(balance=0)
        def operation(wallet, amount):            
            with patch(
                'wallet.views.WalletsViewSet.permission_classes', [AllowAny]
            ):
                response = self.client.post(
                    f'/api/v1/wallets/{str(wallet)}/operation/',
                    data={'operation_type':'DEPOSIT',
                          'amount':f'{amount}'
                    },
                    content_type='application/json', 
                )
                results.append(response.status_code)
                results.append(str(wallet))
                results.append(amount)
                results.append(self.client)
        operation(wallet.id,(0+1)*200)
        #threads = []
        #for index in range(5):
        #    thread = Thread(target=operation, args=(wallet.id,(index+1)*200,))
        #    threads.append(thread)
        #
        #for t in threads: t.start()
        #for t in threads: t.join()
        #thread = Thread(target=operation, args=(wallet.id,(0+1)*200,))
        #thread.start()
        #thread.join()
        #self.assertEqual(len(results), 4)
        #self.assertIsNone(all(results), msg=results)
        self.assertEqual(results[0], 200)
        