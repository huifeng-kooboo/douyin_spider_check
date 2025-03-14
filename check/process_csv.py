import csv
import os

def process_csv(csv_file='repeat.csv'):
    """
    处理CSV文件，去除第二列链接中的.mp4后缀
    
    参数:
        csv_file: 要处理的CSV文件路径
    """
    print(f"开始处理 {csv_file} 文件...")
    
    # 检查文件是否存在
    if not os.path.exists(csv_file):
        print(f"错误: 找不到文件 {csv_file}")
        return False
    
    # 读取CSV文件
    rows = []
    try:
        with open(csv_file, 'r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            header = next(reader)  # 读取标题行
            rows.append(header)
            
            for row in reader:
                if len(row) >= 2:
                    # 处理第二列，移除.mp4后缀
                    video_name = row[0]
                    download_link = row[1]
                    
                    # 替换.mp4后缀
                    if '.mp4' in download_link:
                        new_link = download_link.replace('.mp4', '')
                        row[1] = new_link
                
                rows.append(row)
        
        # 写回CSV文件
        with open(csv_file, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerows(rows)
        
        print(f"处理完成! 已成功移除链接中的.mp4后缀")
        return True
    
    except Exception as e:
        print(f"处理文件时出错: {e}")
        return False

if __name__ == "__main__":
    process_csv() 