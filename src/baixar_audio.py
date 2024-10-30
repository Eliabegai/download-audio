import yt_dlp
import os
import sys
import re
import shutil
from colorama import Fore, Back, Style, init
import subprocess
from instalar_FFmpeg import instalar_ffmpeg


os.getcwd()
init(autoreset=True)

total_videos = 0
current_video = 0

# Caminho da pasta onde o executável está localizado
if getattr(sys, 'frozen', False):
    # Quando o script está "congelado" pelo PyInstaller
    diretorio_base = os.path.dirname(sys.executable)
else:
    # Quando o script está sendo executado normalmente
    diretorio_base = os.path.dirname(os.path.abspath(__file__))

caminho_cookies = os.path.join(diretorio_base, 'cookies.txt')

def limpar_console():
    if os.name == 'nt':  # Windows
        os.system('cls')
    else:  # Linux e macOS
        os.system('clear')

def my_hook(d):
    global current_video

    if d['status'] == 'finished':
        current_video += 1
        print(f" -> Download concluído: {current_video}/{total_videos}")
    # elif d['status'] == 'downloading':
    #     print(f" ... Baixando vídeo {current_video + 1}/{total_videos}: {d['_percent_str']} concluído")


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
        
def validarTitulo(titulo):
    global total_videos
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
                total_videos = len(info_dict['entries'])
                print(f"Vídeo encontrado: {video_info['title']}")
                return video_info
            else:
                print("Nenhum vídeo encontrado para o título fornecido.")
                return None

        except yt_dlp.utils.DownloadError as e:
            print(f"Erro durante a busca: {e}")
            return None

def verificar_ffmpeg():
    try:
        subprocess.run(['ffmpeg', '-version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError:
        print(f'{Fore.BLUE}{Back.BLACK}FFmpeg está instalado, mas ocorreu um erro.{Style.RESET_ALL}')
        return False
    except FileNotFoundError:
        print(f'{Fore.BLUE}{Back.BLACK}FFmpeg não está instalado ou não está no PATH.{Style.RESET_ALL}')
        instalar_ffmpeg()
        return False

def downloadAudio(url_download, output_path):

    audio_folder = os.path.join(output_path, 'audios')
    os.makedirs(audio_folder, exist_ok=True)


    ydl_opts = {
    'format': 'bestaudio/best',
    'outtmpl': os.path.join(audio_folder, '%(title)s.%(ext)s'),
    'noplaylist': True,
    'cookies': caminho_cookies,
    'progress_hooks': [my_hook],                    # Função de hook para monitorar progresso
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
        'progress_hooks': [my_hook],                    # Função de hook para monitorar progresso
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
        'progress_hooks': [my_hook],                    # Função de hook para monitorar progresso
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

largura_terminal = shutil.get_terminal_size().columns

tituloDownload = f'{Fore.YELLOW}{Back.BLACK}DOWNLOAD AUDIO, VÍDEO E PLAYLIST DO YOUTUBE{Style.RESET_ALL}'

menu_texto = '''
    Selecione alguma opção abaixo \n
    > Opção 0: Encerrar Programa
    > Opção 1: Download Audio          (.mp3)
    > Opção 2: Download Vídeo          (.mp4)
    > Opção 3: Download Playlist       (.mp3)
    > Opção 4: Buscar por Título       (.mp3)
'''

def headConsole():
    print("=" * largura_terminal)
    print()
    print(tituloDownload.center(largura_terminal, " "))
    print()

    print("=" * largura_terminal)
    print("." * largura_terminal)
    print(menu_texto)
    print("." * largura_terminal)

if __name__ == "__main__":

    condicao = True

    if os.path.exists(caminho_cookies):
        print(f'{Fore.YELLOW}{Back.BLACK}Arquivo de cookies encontrado.{Style.RESET_ALL}')
    else:
        print(f"Não encontrado arquivo {Fore.RED}{Back.BLACK}cookies.txt{Style.RESET_ALL} na pasta executada.")
        sys.exit(1)
    
    if verificar_ffmpeg():
        print(f'{Fore.YELLOW}{Back.BLACK}FFmpeg instalado.{Style.RESET_ALL}')
    else:
        print(f'{Fore.RED}{Back.BLACK}Por favor, instale o FFmpeg para prosseguir.{Style.RESET_ALL}')
        sys.exit(1)

    headConsole()

    while condicao:

        selectOption = input("Selecione uma Opção: " )
        output_path = os.getcwd() 
        limpar_console()
        headConsole()


        if selectOption == '1':
            print(f'{Fore.YELLOW}{Back.BLACK}\nAudio Selecionado\n{Style.RESET_ALL}')
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
            print(f'{Fore.YELLOW}{Back.BLACK}\nVídeo Selecionado\n{Style.RESET_ALL}')
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
            print(f'{Fore.YELLOW}{Back.BLACK}\nPlaylist Selecionado\n{Style.RESET_ALL}')
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
            print(f'{Fore.YELLOW}{Back.BLACK}\nDownload por Título\n{Style.RESET_ALL}')
            print('Qual o nome da música ou do video que deseja baixar?')
            print('Digite 0 (zero) para retornar')
            
            buscar_video = str(input('Buscar por... : '))
            if(buscar_video == '0'):
                print("retornando...")
                continue
            
            if(buscar_video == ''):
                print('Campo Vazio. retornando...')
                continue

            resultado = validarTitulo(buscar_video)
            
            if resultado:
                print(f"URL do vídeo encontrado: {resultado['webpage_url']}")
                baixar_arquivo = input('Iniciar download? S/N: ').lower()
                if(baixar_arquivo == 's'):
                    print('Iniciando download...')
                    baixar_por_titulo(buscar_video, output_path)
                elif(baixar_arquivo == 'n'):
                    print("Operação cancelada.")

        elif selectOption == '0':
            encerrar = input('Deseja encerrar? S/N: ').lower()
            if(encerrar == 's'):
                condicao = False
                print("\nPrograma encerrado.")
            elif(encerrar == 'n'):
                print("retornando...")
                continue
        else:
            print("Opção inválida!")
