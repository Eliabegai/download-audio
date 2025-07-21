total_videos = 0
current_video = 0

def status_downloading(d):
    global current_video, total_videos

    if d['status'] == 'finished':
        current_video += 1
        print(f" -> Download concluído: {current_video}/{total_videos}")
    # elif d['status'] == 'downloading':
    #     print(f" ... Baixando vídeo {current_video + 1}/{total_videos}: {d['_percent_str']} concluído")
