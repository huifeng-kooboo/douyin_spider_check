# test

from util.douyin_util import DouYinUtil

dy_util = DouYinUtil(sec_uid="MS4wLjABAAAAah62GbBN8fQXHTYIT18z6BV3HB5wt4_H5tYyYn_3Npy56HxUx3uEOk5a5VIL5_Bn")

all_video_list = dy_util.get_all_videos()
for video_id in all_video_list:
    video_info = dy_util.get_video_detail_info(video_id)
    if video_info['is_video'] is True:
        print(f"视频下载链接:{video_info['link']}")
        dy_util.download_video(video_info['link'], f"{video_id}.mp4")
