# coding: utf-8
import os
import re
import shutil
import time
import requests
import base64
from openpyxl import Workbook
from datetime import datetime
from collections import defaultdict


class RecognizeApi(object):
    _api_key = 'nzymeT9x9GogAHNONN25hqA3'
    _api_secret = '99YRCWdrCP9Kle2F6TVEBAVjNgw4gCLL'

    _token_url = 'https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={}&' \
                 'client_secret={}'.format(_api_key, _api_secret)

    accurate_recognize_url = 'https://aip.baidubce.com/rest/2.0/ocr/v1/accurate?access_token={}'

    def __init__(self):
        self.access_token = None
        self._get_access_token()

    def _get_access_token(self):
        resp = requests.get(self._token_url)
        resp.raise_for_status()

        if resp.status_code == 200:
            self.access_token = resp.json().get('access_token')

    def recognize_license(self, image_file):
        f = open(image_file, 'rb')
        ls_f = base64.b64encode(f.read())
        f.close()

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        data = {
            'image': ls_f
        }

        resp = requests.post(self.accurate_recognize_url.format(self.access_token), headers=headers, data=data)

        return resp.json().get('words_result')


class LicenseInfo(object):
    def __init__(self, info: list):
        self.license_name = None     # license name
        self.credit_code = None      # unified social credit code
        self.legal_person = None     # legal person, manager
        self.type = None             # license type
        self._load_info(info)

    def _load_info(self, info):
        for item in info:
            words = str(item.get('words', ''))
            if words:
                if words.startswith('称'):
                    self.license_name = words[1:]
                elif words.startswith('名称'):
                    self.license_name = words[2:]
                elif words.startswith('型'):
                    self.type = words[1:]
                elif words.startswith('类型'):
                    self.type = words[2:]
                elif words.startswith('经营者') or words.startswith('投资人'):
                    self.legal_person = words[3:]
                else:
                    res = re.search(r'[1-9A-GY]{1}[1239]{1}[1-5]{1}[0-9]{5}[0-9A-Z]{10}', words)
                    if res:
                        self.credit_code = res.group()


def read_image(folder):
    files = os.listdir(folder)
    return [os.path.join(folder, file) for file in files]


def reset_file(file, license_name, dst):
    dst_path = os.path.join(dst, license_name + '.jpg')
    shutil.move(file, dst_path)


def main():
    src_folder = 'license_image'
    random = datetime.now().strftime('%Y-%m-%d') + '_' + str(int(time.time()))
    dst_folder = os.path.join('detected_license', random)
    os.makedirs(dst_folder)
    api = RecognizeApi()

    files = read_image(src_folder)
    image_num = len(files)
    success_num = 0
    infos = [['法人', '执照名称', '统一信用代码', '执照类型']]
    temp = defaultdict(list)
    print('find {} images of license totally ...'.format(image_num))

    for idx, file in enumerate(files):
        try:
            data = api.recognize_license(file)
            info = LicenseInfo(data)
            reset_file(file, info.license_name, dst_folder)
            temp[info.legal_person].append(info)
            # temp.get(info.legal_person, list()).append(info)
            # infos.append([info.legal_person, info.license_name, info.credit_code, info.type])

            success_num += 1
            # print(info.license_name, info.credit_code, info.legal_person, info.type)
        except Exception as e:
            print('recognize {}th image failed, reason:{}'.format(idx, e))

    if success_num > 0:
        print('recognize {} license images successfully, and reset these images, save them into {}'.format(success_num, dst_folder))
        for v in temp.values():
            infos.extend([[info.legal_person, info.license_name, info.credit_code, info.type] for info in v])

    try:
        wb = Workbook()
        wb.create_sheet('license info')
        sheet = wb.get_sheet_by_name('license info')
        for info in infos:
            sheet.append(info)
        excel_name = 'license_{}.xls'.format(random)
        wb.save(excel_name)
        print('save license info into {} successfully'.format(excel_name))
    except Exception as e:
        print('save license info failed! reason:{}'.format(e))


if __name__ == '__main__':
    main()
