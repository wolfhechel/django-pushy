from django.test import TestCase

from pushy.exceptions import PushGCMApiKeyException, PushAPNsCertificateException

from pushy.models import Device
from pushy import dispatchers
import pushjack

from .compat import mock



class DispatchersTestCase(TestCase):

    def test_check_cache(self):
        dispatchers.dispatchers_cache = {}

        # Test cache Android
        dispatcher1 = dispatchers.get_dispatcher(Device.DEVICE_TYPE_ANDROID)
        self.assertEquals(dispatchers.dispatchers_cache, {1: dispatcher1})

        # Test cache iOS
        dispatcher2 = dispatchers.get_dispatcher(Device.DEVICE_TYPE_IOS)
        self.assertEquals(dispatchers.dispatchers_cache, {1: dispatcher1, 2: dispatcher2})

        # Final check, fetching from cache
        dispatcher1 = dispatchers.get_dispatcher(Device.DEVICE_TYPE_ANDROID)
        self.assertEquals(dispatchers.dispatchers_cache, {1: dispatcher1, 2: dispatcher2})

    def test_dispatcher_types(self):
        # Double check the factory method returning the correct types
        self.assertIsInstance(dispatchers.get_dispatcher(Device.DEVICE_TYPE_ANDROID), dispatchers.GCMDispatcher)
        self.assertIsInstance(dispatchers.get_dispatcher(Device.DEVICE_TYPE_IOS), dispatchers.APNSDispatcher)

    def test_dispatcher_android(self):
        android = dispatchers.get_dispatcher(Device.DEVICE_TYPE_ANDROID)

        device_key = 'TEST_DEVICE_KEY'
        data = {'title': 'Test', 'body': 'Test body'}

        # Check that we throw the proper exception in case no API Key is specified
        with mock.patch('django.conf.settings.PUSHY_GCM_API_KEY', new=None):
            self.assertRaises(PushGCMApiKeyException, android.send, device_key, data)

        # Check result when canonical value is returned
        response = pushjack.GCMResponse([])
        response.canonical_ids.append(pushjack.GCMCanonicalID(old_id = device_key, new_id=123123))

        gcm = mock.Mock(return_value=response)
        with mock.patch('pushjack.gcm.GCMConnection.send', new=gcm):
            result, canonical_id = android.send(device_key, data)

            self.assertEquals(result, dispatchers.GCMDispatcher.PUSH_RESULT_SENT)
            self.assertEquals(canonical_id, 123123)

        response = pushjack.GCMResponse([])
        response.errors.append(pushjack.GCMInvalidRegistrationError(123))

        # Check not registered exception
        gcm = mock.Mock(return_value=response)
        with mock.patch('pushjack.gcm.GCMConnection.send', new=gcm):
            result, canonical_id = android.send(device_key, data)

            self.assertEquals(result, dispatchers.GCMDispatcher.PUSH_RESULT_NOT_REGISTERED)
            self.assertEquals(canonical_id, 0)

        response = pushjack.GCMResponse([])
        response.errors.append(pushjack.GCMInternalServerError(123))

        # Check other potential errors
        gcm = mock.Mock(return_value=response)
        with mock.patch('pushjack.gcm.GCMConnection.send', new=gcm):
            result, canonical_id = android.send(device_key, data)

            self.assertEquals(result, dispatchers.GCMDispatcher.PUSH_RESULT_EXCEPTION)
            self.assertEquals(canonical_id, 0)


class ApnsDispatcherTests(TestCase):

    dispatcher = None

    device_key = 'TEST_DEVICE_KEY'

    data = {
        'alert': 'Test'
    }

    def setUp(self):
        self.dispatcher = dispatchers.get_dispatcher(Device.DEVICE_TYPE_IOS)

    @mock.patch('django.conf.settings.PUSHY_APNS_CERTIFICATE_FILE', new=None)
    def test_certificate_exception_on_send(self):
        self.assertRaises(PushAPNsCertificateException, self.dispatcher.send, self.device_key, self.data)

    @mock.patch('pushjack.apns.APNSClient.send')
    def test_invalid_token_error_response(self, send):
        send.return_value = pushjack.APNSResponse([self.device_key],
                                                  [],
                                                  [pushjack.APNSInvalidTokenError(0)])

        self.assertEqual(self.dispatcher.send(self.device_key, self.data),
                         (dispatchers.Dispatcher.PUSH_RESULT_NOT_REGISTERED, 0))

        send.return_value = pushjack.APNSResponse([self.device_key],
                                                  [],
                                                  [pushjack.APNSInvalidTokenSizeError(0)])

        self.assertEqual(self.dispatcher.send(self.device_key, self.data),
                         (dispatchers.Dispatcher.PUSH_RESULT_NOT_REGISTERED, 0))

    @mock.patch('pushjack.apns.APNSClient.send')
    def test_push_exception(self, send):
        send.return_value = pushjack.APNSResponse([self.device_key],
                                                  [],
                                                  [pushjack.APNSInvalidPayloadSizeError(0)])

        self.assertEqual(self.dispatcher.send(self.device_key, self.data),
                         (dispatchers.Dispatcher.PUSH_RESULT_EXCEPTION, 0))

    @mock.patch('pushjack.apns.APNSClient.send')
    def test_push_sent(self, send):
        send.return_value = pushjack.APNSResponse([self.device_key],
                                                  [],
                                                  [])

        self.assertEqual(self.dispatcher.send(self.device_key, self.data),
                         (dispatchers.Dispatcher.PUSH_RESULT_SENT, 0))