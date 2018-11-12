# import datetime as dt
import logging

from django import forms
from django.conf import settings
# from django.utils.translation import gettext

import requests
# from govuk_forms.fields import YearField, SplitDateField


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
#
# class CustomYearField(YearField):
#     def __init__(self, era_boundary=None, **kwargs):
#         self.current_year = dt.datetime.now().year
#         min_value = self.current_year
#         max_value = self.current_year + 1
#         self.century = 100 * (self.current_year // 100)
#         if era_boundary is None:
#             # 2-digit dates are a minimum of 10 years ago by default
#             era_boundary = self.current_year - self.century - 10
#         self.era_boundary = era_boundary
#         bounds_error = gettext('Year should be between %(min_value)s and %(max_value)s.') % {
#             'min_value': min_value,
#             'max_value': max_value,
#         }
#         options = {
#             'min_value': min_value,
#             'max_value': max_value,
#             'error_messages': {
#                 'min_value': bounds_error,
#                 'max_value': bounds_error,
#                 'invalid': gettext('Enter year as a number.'),
#             }
#         }
#         options.update(kwargs)
#         super(forms.IntegerField, self).__init__(**options)
#
#
# class CustomSplitDateField(SplitDateField):
#     def __init__(self, *args, **kwargs):
#         day_bounds_error = gettext('Day should be between 1 and 31.')
#         month_bounds_error = gettext('Month should be between 1 and 12.')
#
#         self.fields = [
#             forms.IntegerField(min_value=1, max_value=31, error_messages={
#                 'min_value': day_bounds_error,
#                 'max_value': day_bounds_error,
#                 'invalid': gettext('Enter day as a number.')
#             }),
#             forms.IntegerField(min_value=1, max_value=12, error_messages={
#                 'min_value': month_bounds_error,
#                 'max_value': month_bounds_error,
#                 'invalid': gettext('Enter month as a number.')
#             }),
#             CustomYearField(),
#         ]
#
#         super(forms.MultiValueField, self).__init__(self.fields, *args, **kwargs)
