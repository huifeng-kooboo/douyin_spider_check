# test

from util.douyin_util import DouYinUtil

dy_util = DouYinUtil(sec_uid="MS4wLjABAAAAah62GbBN8fQXHTYIT18z6BV3HB5wt4_H5tYyYn_3Npy56HxUx3uEOk5a5VIL5_Bn")

all_video_list = dy_util.get_all_videos()

print('end')
