import yt_dlp
import os
import sys
import re

os.getcwd()

total_videos = 0
current_video = 0
caminho_cookies = f"{os.getcwd()}/cookies.txt"

def my_hook(d):
    global current_video
    if d['status'] == 'finished':
        current_video += 1
        print(f" -> Download concluído: {current_video}/{total_videos}")
    # elif d['status'] == 'downloading':
    #     print(f"Baixando vídeo {current_video + 1}/{total_videos}: {d['_percent_str']} concluído")


def validar_url(url):
    global total_videos
    url_pattern = re.compile(r'^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+$')
    if not url_pattern.match(url):
        print("URL inválida: não corresponde ao formato esperado.")
        return False
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'default_search': 'ytsearch',
        'cookies': caminho_cookies,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            print("URL válida! Título:", info.get("title", "Título desconhecido"))
            if 'entries' in info:
                total_videos = len(info['entries'])
                print(f"Total de vídeos na playlist: {total_videos}")
            return True
        except yt_dlp.utils.DownloadError:
            print("URL inválida ou conteúdo indisponível.")
            return False
        
def validarTitle(titulo):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'default_search': 'ytsearch',
        'cookies': caminho_cookies,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:

            info_dict = ydl.extract_info(titulo, download=False)

            if 'entries' in info_dict and info_dict['entries']:
                video_info = info_dict['entries'][0]
                print(f"Vídeo encontrado: {video_info['title']}")
                return video_info
            else:
                print("Nenhum vídeo encontrado para o título fornecido.")
                return None

        except yt_dlp.utils.DownloadError as e:
            print(f"Erro durante a busca: {e}")
            return None

def downloadAudio(url_download, output_path):

    audio_folder = os.path.join(output_path, 'audios')
    os.makedirs(audio_folder, exist_ok=True)


    ydl_opts = {
    'format': 'bestaudio/best',
    'outtmpl': os.path.join(audio_folder, '%(title)s.%(ext)s'),
    'noplaylist': True,
    'cookies': caminho_cookies,
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'nooverwrites': True,
    'quiet': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url_download])
    
    print("Download e conversão concluídos!")

def downloadVideo(url_download, output_path):

    audio_folder = os.path.join(output_path, 'audios')
    os.makedirs(audio_folder, exist_ok=True)
    
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': os.path.join(audio_folder, '%(title)s.%(ext)s'),
        'noplaylist': True,
        'cookies': caminho_cookies,
        'merge_output_format': 'mp4',
        'nooverwrites': True,
        'quiet': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url_download])

    print("Download do vídeo concluído!")

def downloadPlaylist(url_download, output_path):

    global total_videos, current_video

    audio_folder = os.path.join(output_path, 'audios/playlist')
    os.makedirs(audio_folder, exist_ok=True)


    ydl_opts = {
    'format': 'bestaudio/best',
    'outtmpl': os.path.join(audio_folder, '%(title)s.%(ext)s'),
    'noplaylist': False,
    'cookies': caminho_cookies,
    'extractaudio': True,
    'progress_hooks': [my_hook],                    # Função de hook para monitorar progresso
    'ignoreerrors': True,
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'nooverwrites': True,
    'quiet': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url_download])
    
    print("Download e conversão concluídos!")

def baixar_por_titulo(titulo, output_path):
    
    audio_folder = os.path.join(output_path, 'audios')
    os.makedirs(audio_folder, exist_ok=True)
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(audio_folder, '%(title)s.%(ext)s'),
        'default_search': 'ytsearch',
        'noplaylist': True,
        'ignoreerrors':True,
        'cookies': caminho_cookies,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'nooverwrites': True,
        'quiet': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        print(f"Buscando e baixando: '{titulo}'")
        ydl.download([titulo])
    
    print("Download e conversão concluídos!")


if __name__ == "__main__":

    condicao = True

    if os.path.exists(caminho_cookies):
        print('\033[13;40mArquivo de cookies encontrado.\033[m')
    else:
        print("Não encontrado arquivo \033[33;20mcoockies.txt\033[m na pasta executada.")
        sys.exit(1) 

    print('\033[33;40m\nDOWNLOAD AUDIO OU VIDEO\n\033[m')
    print(
    '''==================================
    Opção 0: Encerrar Programa
    Opção 1: Download Audio
    Opção 2: Download Vídeo
    Opção 3: Download PLaylist
    Opção 4: Buscar por Título
================================== \n''')

    while condicao:

        selectOption = input("\nSelect Option: " )
        output_path = os.getcwd()  # Obtém o diretório atual


        if selectOption == '1':
            print('\n---------------------------------------------------\n')
            print('\033[33;40m\nAudio Selecionado\n\033[m')
            print('Digite 0 (zero) para retornar')
            url_Audio = input('Insira a url aqui: ')
            if(url_Audio == '0'):
                print("retornando...")
                continue
            if(url_Audio == ''):
                print('Campo Vazio. retornando...')
                continue

            print('Validando url...')
            validUrl = validar_url(url_Audio)
            if validUrl:
                baixar_arquivo = input('Iniciar download? S/N: ').lower()
                if(baixar_arquivo == 's'):
                    print("\nIniciando download...")
                    downloadAudio(url_Audio, output_path)
                else:
                    print("Download cancelado.")
            else:
                print("Falha na validação da URL. Verifique e tente novamente.")

        elif selectOption == '2':
            print('\n---------------------------------------------------\n')
            print('\033[33;40m\nVídeo Selecionado\n\033[m')
            print('Digite 0 (zero) para retornar')
            url_Video = str(input('Insira a url aqui: '))

            if(url_Video == '0'):
                print("retornando...")
                continue
            
            if(url_Video == ''):
                print('Campo Vazio. retornando...')
                continue

            print('Validando url...')
            if validar_url(url_Video):
                baixar_arquivo = input('Iniciar download? S/N: ').lower()
                if(baixar_arquivo == 's'):
                    print("Iniciando download...")
                    downloadVideo(url_Video, output_path)
                else:
                    print("Download cancelado.")
            else:
                print("Falha na validação da URL. Verifique e tente novamente.")

        elif selectOption == '3':
            print('\n---------------------------------------------------\n')
            print('\033[33;40m\nPlaylist Selecionado\n\033[m')
            print('Digite 0 (zero) para retornar')
            url_Playlist = str(input('Insira a url aqui: '))

            if(url_Playlist == '0'):
                print("retornando...")
                continue

            if(url_Playlist == ''):
                print('Campo Vazio. retornando...')
                continue

            print('Validando url...')
            if validar_url(url_Playlist):
                baixar_arquivo = input('Iniciar download? S/N: ').lower()
                if(baixar_arquivo == 's'):
                    print("Iniciando download da playlist...")
                    downloadPlaylist(url_Playlist, output_path)
                else:
                    print("Download cancelado.")
            else:
                print("Falha na validação da URL. Verifique e tente novamente.")

        elif selectOption == '4':
            print('\n---------------------------------------------------\n')
            print('\033[33;40m\nDownload por Título\n\033[m')
            print('Qual o nome do título do video que deseja baixar?')
            print('Digite 0 (zero) para retornar')
            
            buscar_video = str(input('Buscar por... : '))
            if(buscar_video == '0'):
                print("retornando...")
                continue
            
            if(buscar_video == ''):
                print('Campo Vazio. retornando...')
                continue

            resultado = validarTitle(buscar_video)
            
            if resultado:
                print(f"URL do vídeo encontrado: {resultado['webpage_url']}")
                baixar_arquivo = input('Iniciar download? S/N: ').lower()
                if(baixar_arquivo == 's'):
                    print('iniciando download')
                    baixar_por_titulo(buscar_video, output_path)
                elif(baixar_arquivo == 'n'):
                    print("Operação cancelada.")

        elif selectOption == '0':
            print('\n---------------------------------------------------\n')
            encerrar = input('Deseja encerrar? S/N: ').lower()
            if(encerrar == 's'):
                condicao = False
                print("\nPrograma encerrado.")
            elif(encerrar == 'n'):
                print("retornando...")
                continue
        else:
            print("Opção inválida!")
