import sys

total_videos = 1
current_video = 0

def reset_and_set_total(total):
    """Reseta o progresso e define o total de vídeos/itens."""
    global total_videos, current_video
    total_videos = total
    current_video = 0
    # print(f"DEBUG: Total set to {total_videos}. Current reset to {current_video}.") # Linha de debug opcional

def status_downloading(d):
    global current_video, total_videos

    if d['status'] == 'finished':
        current_video += 1
        print(f" -> Download concluído: {current_video}/{total_videos}")
        print('Aguardando processamento...\n')
        sys.stdout.flush()
    if d['status'] == 'downloading':
        percent_str = d.get('_percent_str', '??%')
        downloaded_str = d.get('_downloaded_bytes_str', '??MiB')
        total_str = d.get('_total_bytes_str', '??MiB')
        speed_str = d.get('_speed_str', '??MiB/s')

        if total_videos > 1:
            print(f"[download] Video {current_video + 1}/{total_videos}: {percent_str} of {total_str} at {speed_str}", end='\r')
            print(" " * 80, end='\r')
        sys.stdout.flush()