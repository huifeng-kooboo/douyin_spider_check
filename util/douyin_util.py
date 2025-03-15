import json
import requests
import time
import os
import urllib.request
import argparse
import pandas as pd
import csv
from datetime import datetime

from tools.util import get_current_time_format, generate_url_with_xbs, sleep_random
from config import IS_SAVE, SAVE_FOLDER, USER_SEC_UID, IS_WRITE_TO_CSV, LOGIN_COOKIE, CSV_FILE_NAME
import requests

import logging

# 配置日志
logging.basicConfig(level=logging.DEBUG)

# 创建日志器
logger = logging.getLogger(__name__)


__all__ = ['DouYinUtil']

class DouYinUtil(object):

    def __init__(self, sec_uid: str):
        """
        :param sec_uid: 抖音id
        """
        self.sec_uid = sec_uid
        self.is_save = IS_SAVE
        self.save_folder = SAVE_FOLDER
        if not os.path.exists(self.save_folder):
            os.mkdir(self.save_folder)
        self.is_write_to_csv = IS_WRITE_TO_CSV
        self.csv_name = CSV_FILE_NAME
        self.video_api_url = ''
        self.api_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
            'Referer': 'https://www.douyin.com/',
            'Cookie': LOGIN_COOKIE
        }
        self.cursor = 0
        self.videos_list = []  # 视频列表id
        self.video_info_list = []
        self.video_info_dict = {}
        self.stop_flag = False  # 默认不停止

    def get_user_video_info(self, url: str):
        res = requests.get(url, headers=self.api_headers)
        res.encoding = 'utf-8'
        res_text = res.text
        return json.loads(res_text)

    def get_all_videos(self):
        """
        获取所有的视频
        :return:
        """
        while not self.stop_flag:
            self.video_api_url = f'https://www.douyin.com/aweme/v1/web/aweme/post/?aid=6383&sec_user_id={self.sec_uid}&count=35&max_cursor={self.cursor}&cookie_enabled=true&platform=PC&downlink=10'
            xbs = generate_url_with_xbs(self.video_api_url, self.api_headers.get('User-Agent'))
            user_video_url = self.video_api_url + '&X-Bogus=' + xbs
            print(f'访问url:{user_video_url}')
            user_info = self.get_user_video_info(user_video_url)   
            aweme_list = user_info['aweme_list']
            for aweme_info in aweme_list:
                self.video_info_list.append(aweme_info)
                self.video_info_dict.setdefault(aweme_info['aweme_id'], aweme_info)
                self.videos_list.append(aweme_info['aweme_id'])
            if int(user_info['has_more']) == 0:
                print(f'stop_more')
                self.stop_flag = True
            else:
                self.cursor = user_info['max_cursor']
                # self.stop_flag = True
            sleep_random()
        return self.videos_list

    def download_video(self, video_url: str, file_name: str = None):
        """
        下载视频
        :param video_url: 视频地址
        :param file_name: 视频保存文件名: 默认为空
        :return:
        """
        logger.info(f"下载视频: {video_url}")
        if not self.is_save:
            logger.info("当前不需要保存")
            return
        save_folder = f"{self.save_folder}/{self.sec_uid}"
        if not os.path.exists(save_folder):
            os.mkdir(save_folder)
        real_file_name = f"{save_folder}/{file_name}"
        logger.info(f"下载url:{video_url}\n保存文件名:{real_file_name}")
        if os.path.exists(real_file_name):
            os.remove(real_file_name)

        # 发送GET请求
        headers_ = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
            'Referer': video_url,
            'cookie': LOGIN_COOKIE
        }
        response = requests.get(video_url, stream=True, headers=headers_)

        # 检查请求是否成功
        if response.status_code == 200:
            # 打开一个本地文件用于保存下载的视频
            with open(real_file_name, 'wb') as f:
                # 下载大文件需这样处理
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.info("下载完成")
        else:
            logger.info(f"错误{response.status_code}")
        # urllib.request.urlretrieve(video_url, real_file_name)

    def download_images(self, image_list: list, image_dir: str = None):
        """
        下载图片
        :param image_list: 图片地址
        :param file_name: 图片目录: 默认为空
        :return:
        """
        if not self.is_save:
            logger.info("当前不需要保存")
            return

        parent_folder = f"{self.save_folder}/{self.sec_uid}"
        if not os.path.exists(parent_folder):
            os.mkdir(parent_folder)
        save_folder = f"{self.save_folder}/{self.sec_uid}/{image_dir}"

        logger.info(f"save-dir:{save_folder}")

        num = 1
        if not os.path.exists(save_folder):
            os.mkdir(save_folder)
        for image_url in image_list:
            num += 1
            logger.info(f"image_url:{image_url} {num}")
            real_file_name = f"{save_folder}/{num}.jpeg"
            logger.info(f"下载url:{image_url}\n保存文件名:{real_file_name}")
            if os.path.exists(real_file_name):
                os.remove(real_file_name)
            urllib.request.urlretrieve(image_url, real_file_name)

    def get_video_detail_info(self, video_id: str):
        """
        获取视频详细信息
        :param video_id: 视频id
        :return:
        """
        default_response = {
            'video_id': video_id,  # 视频id
            'link': 'None',  # 视频链接
            'is_video': True,  # 是否为视频
            'title': 'None',  # 标题
            'thumb_up_num': 0,  # 点赞数
            'comment_num': 0,  # 评论数
            'cover_url': 'http://www.baidu.com',  # 视频封面
            'publish_time': '',  # 发布日期
            'record_time': '记录日期',  # 更新日期
            "preview_title": ""
        }
        res_info = self.video_info_dict.get(video_id, None)
        if res_info is None:
            return default_response
        default_response['title'] = res_info['desc']
        if res_info.get('preview_title') is not None:
            default_response["preview_title"] = res_info["preview_title"]
        create_time = res_info['create_time']
        local_time = time.localtime(create_time)
        local_time_str = time.strftime("%Y-%m-%d %H:%M:%S", local_time)
        default_response['publish_time'] = local_time_str
        default_response['record_time'] = get_current_time_format()
        if res_info['images'] is None:
            default_response['link'] = res_info["video"]["play_addr"]["url_list"][0]
            default_response['cover_url'] = res_info["video"]["cover"]["url_list"][0]
            default_response['is_video'] = True
        else:
            default_response['link'] = list(map(lambda x: x["url_list"][-1], res_info["images"]))
            default_response['is_video'] = False
        default_response['thumb_up_num'] = res_info['statistics']['admire_count']
        default_response['comment_num'] = res_info['statistics']['comment_count']
        return default_response


if __name__ == '__main__':
    import sys
    
    logger.info("有问题请联系微信：ytouching （备注来意！！！！！！！！！！！！！！！！！！！！！）")
    
    # 设置日期过滤范围
    start_date = datetime.strptime("2024-07-30", "%Y-%m-%d")
    end_date = datetime.strptime("2024-09-16", "%Y-%m-%d")
    logger.info(f"将只下载发布日期在 {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')} 之间的视频")
    
    # 用于统计日期范围内的视频总数
    total_videos_in_date_range = 0
    
    sec_ids = [
    "MS4wLjABAAAAfwC4FNWTyjrCI05j514BEhZgodntZCCMMKP3fEk20PYdlkAVWzn0EAqHTUpqTiH1",
    "MS4wLjABAAAAFAF36d5hKBnA74iq_toEEBrSCff07mudC3oZOdY4nVqRL0QCeD-n6KJMvxHsB6lM",
    "MS4wLjABAAAAohVm6-PayCV2NeT8yaurUd-HvOS3YW7HLFbU2LfFN6NGLjgonkcQGTdqGKB_LnzU",
    "MS4wLjABAAAArDbPwEQ2-blopFAhCthfWmwXTeZM3QfJaW3hZNT3EsoMEcJrwLMvy7XU6y14iR9O",
    "MS4wLjABAAAAdt1dNzq23RsPR3isjQRBUazfFYWWRd8nyPnJni0g_r0",
    "MS4wLjABAAAA8vwd_A2Ft3LarCNk38HXWvOhXIh2ZsF2pWnn9j5EMRIujMCZpiOSecRS4B0wvVuS",
    "MS4wLjABAAAAiqWtQKLA8StUOm3Z5abbxodZg7AyEUeMlpQDzChL7Y0o6ygcRe_O3TTo2FRwKmMy",
    "MS4wLjABAAAABioHQCe9sw_NYkBXdHa23PMHm1qCxMtFZdg6C7_1Pp2BACa8ME_bzzsmAdhc3pqL",
    "MS4wLjABAAAA-4fKwdw3AFO6CY0A97AAasJdfwOaQFBobyJ8Vk0y4zdH5UET79gdskwp-jYrQWDi",
    "MS4wLjABAAAANzGtzHGOtFZCEnV3XypfciET73xOEHhbc2iFyx14sjO3pNjb7cnt8voMgJdtUl4L",
    "MS4wLjABAAAAEcNs6zzDj7ofHRYpxoE-LbGuZlL_-dKGPwn-DEZ9zg0",
    "MS4wLjABAAAAah62GbBN8fQXHTYIT18z6BV3HB5wt4_H5tYyYn_3Npy56HxUx3uEOk5a5VIL5_Bn",
    "MS4wLjABAAAA3vvQZ2F1UkKzRbcl4zrypMlx3n6345y0EeEpIZf72aA",
    "MS4wLjABAAAAVgStqIhIyX1HyzcEFHOEPi6BQCYjw1HrHeppCwmWM_k",
    "MS4wLjABAAAAO1PVQMxBsB3audKz5pc5Cm6eQ368wk3oJmw4mK5HgkDWd2JO2ClvRtvY6m_3CJc9",
    "MS4wLjABAAAAQN85UyUcpsi_9VlrskDNzOOo7kTccAYHycj9fn8dSU4",
    "MS4wLjABAAAAsJmdMboFgYWqXCzExzO9WwlytavU2A8IniUMgwpyAhMnjxi-9fcgU474cRZGo5o0",
    "MS4wLjABAAAAhtCelSgwzK1ZosNsMgYGSWuftfrBg472xO8qFFjYFMnFzPb08zB0zsx8qTaoDJeE",
    "MS4wLjABAAAAV74QxZyGavgsZwvtKO0EfOY87-ZyfU_0M9fWl7VwWNH-vk7TNwnzbxnMgG5Qphda",
    "MS4wLjABAAAAADo6DBTTU7QwJ9E54WwS4nlsO9Y0jm6j88gWpA5-rm0",
    "MS4wLjABAAAAnqxgTt0uwh1CIKVhzDCA45hXqN9wLUz_N5rW-b2EHME",
    "MS4wLjABAAAAfJCwsItqbHTARZ3AdcPKCngvQQD1Rml-lE9TpjP9o9fcI_XeZLm0-mIcArslZ-vT",
    "MS4wLjABAAAAr4GH4iJraDRWlpLAGO5mEqEOl0VYLz9FzZrSXmp1vvFQ0JX8H_gTKEJH7YF6cvyC",
    "MS4wLjABAAAAUbxcnzAjexXMGet8fyXcakK2-G7An1-_2Bxqlg4JC4EFOflnfuXx032yVPSXKIyM",
    "MS4wLjABAAAAWzVO_Kt-uvi8lTCVo17KmsLkKOs7a4WlkCxGzVytWkGGF7flXWMap35sxiURj2cL",
    "MS4wLjABAAAAdXNU5N0mJFlKyONz-OcIAXkmKd-NJo78Zs7NENSZHE2u7w_ol4hfx1Hdzw2M6bZF"
 ]
    for sec in sec_ids:
        params_list_size = len(sys.argv)
        USER_SEC_UID = sec

        print(f"当前传入的参数：SEC_ID：{USER_SEC_UID}\n SAVE_FOLDER:{SAVE_FOLDER}")
        if not os.path.exists(SAVE_FOLDER):
            os.mkdir(SAVE_FOLDER)

        dy_util = DouYinUtil(sec_uid=USER_SEC_UID)
        all_video_list = dy_util.get_all_videos()
        print(f"当前需要下载的视频列表数量为:{len(all_video_list)}")
        
        # 当前用户在日期范围内的视频数
        user_videos_in_date_range = 0
        
        csvVideos = []
        for video_id in all_video_list:
            video_info = dy_util.get_video_detail_info(video_id)
            
            # 检查发布日期是否在指定范围内
            publish_time = video_info.get('publish_time', '')
            if publish_time:
                try:
                    publish_date = datetime.strptime(publish_time, "%Y-%m-%d %H:%M:%S")
                    if not (start_date <= publish_date <= end_date):
                        logger.info(f"视频 {video_id} 的发布日期 {publish_time} 不在指定范围内，跳过下载")
                        continue
                    else:
                        logger.info(f"视频 {video_id} 的发布日期 {publish_time} 在指定范围内，将下载")
                        user_videos_in_date_range += 1
                        total_videos_in_date_range += 1
                except ValueError as e:
                    logger.error(f"解析发布日期出错: {e}，将继续下载")
            
            if video_info['is_video'] is True:
                logger.info(f"video_link:{video_info['link']}")
                dy_util.download_video(video_info['link'], f"{video_id}.mp4")
            if video_info["is_video"] is False:
                dy_util.download_images(video_info["link"], f"{video_id}")
            title = video_info["title"]
            preview_title = video_info["preview_title"]
            logger.info(f"file:{video_id}.mp4,title:{title} , preview_title:{preview_title}")
            video_info["link"] = video_id
            video_info["video_id"] = f"id:{video_id}"
            csvVideos.append(video_info)
        
        print(f"用户 {USER_SEC_UID} 在 {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')} 期间发布了 {user_videos_in_date_range} 个视频")
        
        try:
            CSV_FILE_NAME = f'/Users/duhuifeng/code/csv/sec_{USER_SEC_UID}.csv'
            data = pd.DataFrame(csvVideos)
            csvHeaders = ["视频id", "视频链接", "是否为视频", "标题", "点赞数", "评论数", "视频封面", "发布日期",
                      "更新日期",
                      "预览标题"]
            data.to_csv(CSV_FILE_NAME, header=csvHeaders, index=False, mode='a+', encoding='utf-8')
            try:
                data.to_csv(CSV_FILE_NAME, header=False, index=False, mode='a+', encoding='utf-8')
            except UnicodeEncodeError:
                logger.info("编码错误, 该数据无法写到文件中, 直接忽略该数据")
        except Exception as e:
            logger.info(e)
    
    # 输出统计结果
    print(f"\n统计结果：在 {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')} 期间，所有用户共发布了 {total_videos_in_date_range} 个视频")

