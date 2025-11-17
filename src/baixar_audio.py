import yt_dlp
import os
import sys
import shutil
from colorama import Fore, Back, Style, init
import subprocess
from functions_download import downloadAudio, downloadVideo, downloadPlaylist, baixar_por_titulo
from validate import validar_url

os.getcwd()
init(autoreset=True)

if getattr(sys, 'frozen', False):
    diretorio_base = os.path.dirname(sys.executable)
else:
    diretorio_base = os.path.dirname(os.path.abspath(__file__))

caminho_cookies = os.path.join(diretorio_base, 'cookies.txt')

def limpar_console():
    if os.name == 'nt':  # Windows
        os.system('cls')
    else:  # Linux e macOS
        os.system('clear')
        
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
        return False

largura_terminal = (shutil.get_terminal_size().columns - 10)
largura_terminal_title = shutil.get_terminal_size().columns
# largura_terminal = 85
# largura_terminal_title = 95

tituloDownload = f'{Fore.YELLOW}{Back.BLACK}DOWNLOAD AUDIO, VÍDEO E PLAYLIST DO YOUTUBE{Style.RESET_ALL}'

menu_texto = '''
    Selecione alguma opção abaixo \n
    > Opção 0: Encerrar Programa
    > Opção 1: Download do Audio          (.mp3)
    > Opção 2: Download do Vídeo          (.mp4)
    > Opção 3: Download da Playlist       (.mp3)
    > Opção 4: Buscar por Título          (.mp3)
'''

def headConsole():
    print("=" * largura_terminal)
    print("\n", tituloDownload.center(largura_terminal_title, " "), "\n")
    print("=" * largura_terminal)
    print(menu_texto)
    
def printHeadConsole():
    print("=" * largura_terminal)
    print("\n", tituloDownload.center(largura_terminal_title, " "), "\n")
    print("=" * largura_terminal)

def printMenu():
    print(menu_texto)

if __name__ == "__main__":

    if os.path.exists(caminho_cookies):
        print(f'{Fore.YELLOW}{Back.BLACK}Arquivo de cookies encontrado.{Style.RESET_ALL}')
    else:
        print(f"Não encontrado arquivo {Fore.RED}{Back.BLACK}cookies.txt{Style.RESET_ALL} na pasta executada.\nPara alguns downloads pode ser necessário o arquivo.")
    
    print(f'{Fore.YELLOW}{Back.BLACK}Verificando FFmpeg...{Style.RESET_ALL}')
    
    if verificar_ffmpeg():
        print(f'{Fore.YELLOW}{Back.BLACK}FFmpeg instalado.{Style.RESET_ALL}')
    else:
        print(f'{Fore.RED}{Back.BLACK}Por favor, instale o FFmpeg para prosseguir.{Style.RESET_ALL}')
        sys.exit(1)

    headConsole()
    output_path = os.path.join(diretorio_base, 'downloads')

    while True:

        selectOption = input("Selecione uma opção: > " )

        if selectOption == '1':
            limpar_console()
            printHeadConsole()
            print(f'{Fore.YELLOW}{Back.BLACK}\n   Baixar audio selecionado   \n{Style.RESET_ALL}')
            print('Digite 0 (zero) para retornar')
            url_Audio = input('Insira a url aqui: ')
            
            if(url_Audio == '0'):
                print("retornando...")
                printMenu()
                continue
            if(url_Audio == ''):
                print('Campo vazio. retornando...')
                printMenu()
                continue

            print('Validando url...')
            validUrl, titulo_audio = validar_url(url_Audio, caminho_cookies)
            if validUrl:
                baixar_arquivo = input(f'Deseja baixar o audio "{titulo_audio}"? S/N: ').lower()
                if(baixar_arquivo == 's'):
                    print("\nIniciando download...")
                    
                    final_path = downloaded_file_path = downloadAudio(url_Audio, output_path)

                    print("Downdoad concluído!")
                    print(f'\nArquivo salvo em: {final_path}/')
                    printMenu()
                else:
                    print("Download cancelado.")
                    printMenu()
            else:
                print("Falha na validação da URL. Verifique e tente novamente.")
                printMenu()

        elif selectOption == '2':
            limpar_console()
            printHeadConsole()
            print(f'{Fore.YELLOW}{Back.BLACK}\n   Vídeo Selecionado   \n{Style.RESET_ALL}')
            print('Digite 0 (zero) para retornar')
            url_Video = str(input('Insira a url aqui: '))

            if(url_Video == '0'):
                print("retornando...")
                printMenu()
                continue
            
            if(url_Video == ''):
                print('Campo Vazio. retornando...')
                printMenu()
                continue

            print('Validando url...')
            if validar_url(url_Video):
                baixar_arquivo = input('Iniciar download? S/N: ').lower()
                if(baixar_arquivo == 's'):
                    print("Iniciando download...")
                    final_path = downloadVideo(url_Video, output_path)
                    
                    print("Downdoad concluído!")
                    print(f'\nArquivo salvo em: {final_path}/')
                    printMenu()
                    
                else:
                    print("Download cancelado.")
                    printMenu()
            else:
                print("Falha na validação da URL. Verifique e tente novamente.")
                printMenu()

        elif selectOption == '3':
            limpar_console()
            printHeadConsole()
            print(f'{Fore.YELLOW}{Back.BLACK}\n   Playlist Selecionado   \n{Style.RESET_ALL}')
            print('Digite 0 (zero) para retornar')
            url_Playlist = str(input('Insira a url aqui: '))

            if(url_Playlist == '0'):
                print("retornando...")
                printMenu()
                continue

            if(url_Playlist == ''):
                print('Campo Vazio. retornando...')
                printMenu()
                continue

            print('Validando url...')
            if validar_url(url_Playlist):
                baixar_arquivo = input('Iniciar download? S/N: ').lower()
                if(baixar_arquivo == 's'):
                    print("Iniciando download da playlist...")
                    
                    final_path = downloadPlaylist(url_Playlist, output_path)
                    
                    print("Downdoad concluído!")
                    print(f'\nArquivo salvo em: {final_path}/')
                    printMenu()
                    
                else:
                    print("Download cancelado.")
                    printMenu()
            else:
                print("Falha na validação da URL. Verifique e tente novamente.")
                printMenu()

        elif selectOption == '4':
            limpar_console()
            printHeadConsole()
            print(f'{Fore.YELLOW}{Back.BLACK}\n   Download por Título   \n{Style.RESET_ALL}')
            print('Qual o nome da música ou do video que deseja baixar?')
            print('Digite 0 (zero) para retornar')
            
            buscar_video = str(input('Buscar por... : '))
            if(buscar_video == '0'):
                print("retornando...")
                printMenu()
                continue
            
            if(buscar_video == ''):
                print('Campo Vazio. retornando...')
                printMenu()
                continue

            resultado = validarTitulo(buscar_video)
            
            if resultado:
                print(f"URL do vídeo encontrado: {resultado['webpage_url']}")
                baixar_arquivo = input('Iniciar download? S/N: ').lower()
                if(baixar_arquivo == 's'):
                    print('Iniciando download...')
                    final_path = baixar_por_titulo(buscar_video, output_path)
                    
                    print("Downdoad concluído!")
                    print(f'\nArquivo salvo em: {final_path}/')
                    printMenu()
                    
                elif(baixar_arquivo == 'n'):
                    print("Operação cancelada.")
                    printMenu()

        elif selectOption == '0':
            encerrar = input('Deseja encerrar? S/N: ').lower()
            if(encerrar == 's'):
                print("\nPrograma encerrado.")
                break
            elif(encerrar == 'n'):
                print("retornando...")
                printMenu()
                continue
        else:
            print("Opção inválida!")
