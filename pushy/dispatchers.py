import pushjack

from django.conf import settings

from .models import Device
from .exceptions import (
    PushGCMApiKeyException,
    PushAPNsCertificateException
)

dispatchers_cache = {}


class Dispatcher(object):
    PUSH_RESULT_SENT = 1
    PUSH_RESULT_NOT_REGISTERED = 2
    PUSH_RESULT_EXCEPTION = 3

    def send(self, device_key, data):  # noqa
        raise NotImplementedError()


class APNSDispatcher(Dispatcher):

    connection = None

    def __init__(self):
        super(APNSDispatcher, self).__init__()

    @property
    def cert_file(self):
        return getattr(settings, 'PUSHY_APNS_CERTIFICATE_FILE', None)

    @property
    def use_sandbox(self):
        return bool(getattr(settings, 'PUSHY_APNS_SANDBOX', False))

    def establish_connection(self):
        if self.cert_file is None:
            raise PushAPNsCertificateException

        client_class = pushjack.APNSSandboxClient if self.use_sandbox else pushjack.APNSClient

        client = client_class(certificate=self.cert_file)

        assert isinstance(client, pushjack.APNSClient)

        self.connection = client.create_connection()

    def send(self, device_key, data):
        if not self.connection:
            self.establish_connection()

        response = self.connection.send(
            [device_key],
            data.pop('alert', None),
            sound=data.pop('sound', None),
            badge=data.pop('badge', None),
            category=data.pop('category', None),
            content_available=data.pop('content-available', False),
            extra=data or {}
        )

        assert isinstance(response, pushjack.APNSResponse)

        token_error = response.token_errors.get(device_key, None)

        if token_error is None:
            push_result = self.PUSH_RESULT_SENT
        elif isinstance(token_error, (pushjack.APNSInvalidTokenError, pushjack.APNSInvalidTokenSizeError)):
            push_result = self.PUSH_RESULT_NOT_REGISTERED
        else:
            push_result = self.PUSH_RESULT_EXCEPTION

        return push_result, 0


class GCMDispatcher(Dispatcher):

    def send(self, device_key, data):
        gcm_api_key = getattr(settings, 'PUSHY_GCM_API_KEY', None)

        if not gcm_api_key:
            raise PushGCMApiKeyException()

        gcm = pushjack.GCMClient(gcm_api_key)

        response = gcm.send([device_key], message=data)

        canonical_id = 0

        if response.errors:
            error = response.errors[0]

            if isinstance(error, (pushjack.GCMMissingRegistrationError,
                                  pushjack.GCMInvalidRegistrationError)):
                status = self.PUSH_RESULT_NOT_REGISTERED
            else:
                status = self.PUSH_RESULT_EXCEPTION
        else:
            status = self.PUSH_RESULT_SENT

            if response.canonical_ids:
                canonical_id = response.canonical_ids[0].new_id

        return status, canonical_id


def get_dispatcher(device_type):
    if device_type in dispatchers_cache and dispatchers_cache[device_type]:
        return dispatchers_cache[device_type]

    if device_type == Device.DEVICE_TYPE_ANDROID:
        dispatchers_cache[device_type] = GCMDispatcher()
    elif device_type == Device.DEVICE_TYPE_IOS:
        dispatchers_cache[device_type] = APNSDispatcher()

    return dispatchers_cache[device_type]
