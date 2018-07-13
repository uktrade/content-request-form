from django import forms
import requests
from django.conf import settings


class AVFileField(forms.FileField):
    def clean(self, data, initial=None):
        data = super().clean(data, initial=initial)

        if not data:
            return data

        import pdb;
        pdb.set_trace()

        auth = (settings.AV_USERNAME, settings.AV_PASSWORD)
        #files = {"file": open("eicar.txt", "rb")}



        response = requests.post("http://localhost:8090/v2/scan", auth=auth, files=files)

        print(response.text)

        return data


