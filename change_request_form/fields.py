import logging

from django import forms
from django.conf import settings

import requests


logger = logging.getLogger('av-file-check')


class AVFileField(forms.FileField):
    def clean(self, data, initial=None):
        data = super().clean(data, initial=initial)

        if data:
            auth = (settings.AV_USERNAME, settings.AV_PASSWORD)

            raw_response = requests.post(settings.AV_URL, auth=auth, files={"file": data})
            response = raw_response.json()

            data.seek(0)

            if response['malware'] and 'Encrypted' in response['reason']:
                logger.info('Encrypted file {} detected'.format(response['reason']))
                raise forms.ValidationError('You cannot upload encrypted files.')

            elif response['malware']:
                logger.info('Malware {} detected'.format(response['reason']))
                raise forms.ValidationError('File appears to contain Malware.')

        return data
