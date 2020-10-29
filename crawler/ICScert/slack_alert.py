# encoding: utf-8
import json
import requests
import re

class AlertFunc():

    def alert_to_slack(self,alert_text):
        s_url = 'https://hooks.slack.com/services/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'

        dict_headers = {'Content-type': 'application/json'}
        dict_payload = {"text":alert_text}
        json_payload = json.dumps(dict_payload)

        rtn = requests.post(s_url, data=json_payload, headers=dict_headers)
        print(rtn.text)
