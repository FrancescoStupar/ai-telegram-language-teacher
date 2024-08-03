from ibm_watson import TextToSpeechV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
import requests
import json
import base64
import os
import subprocess
from dotenv import load_dotenv

load_dotenv()
ibm_iam = os.getenv("IBM")
ibm_url = os.getenv("IBM_URL")

def convert_mp3_to_ogg(mp3_file_path, ogg_file_path):
    command = ['ffmpeg', '-y', '-i', mp3_file_path, '-c:a', 'libopus', ogg_file_path]
    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, check=True)

def ibm_text_to_speech(text, chat_id, language):
    try:
        mp3_file_path = f"{chat_id}_response.mp3"
        ogg_file_path = f"{chat_id}_response.ogg"

        # Mapping of language to voice.
        language_to_voice = {
            '🇩🇪 German': 'de-DE_BirgitV3Voice',
            '🇪🇸 Spanish': 'es-ES_EnriqueV3Voice',
            '🇮🇹 Italian': 'it-IT_FrancescaV3Voice',
            '🇫🇷 French': 'fr-FR_ReneeV3Voice',
            '🇧🇷 Portuguese': 'pt-BR_IsabelaV3Voice',
            '🇳🇱 Dutch': 'nl-NL_MerelV3Voice',
        }
        
        voice = language_to_voice.get(language)
        pitch_percentage=30
        rate_percentage=20

        # Set up Text to Speech service.
        authenticator = IAMAuthenticator(ibm_iam)
        text_to_speech_service = TextToSpeechV1(authenticator=authenticator)
        text_to_speech_service.set_service_url(ibm_url)

        # Use Text to Speech service to create audio file.
        with open(mp3_file_path, 'wb') as audio_file:
            response = text_to_speech_service.synthesize(text, accept='audio/mp3', voice=voice, pitch_percentage=pitch_percentage, 
            rate_percentage=rate_percentage).get_result()
            audio_file.write(response.content)
        
        # Convert audio file format.
        convert_mp3_to_ogg(mp3_file_path, ogg_file_path)
        try:
            os.remove(mp3_file_path)  # delete response audio file
        except Exception as e:
            print(f"Error occurred while trying to delete response audio file: {e}")
        
        if os.path.exists(ogg_file_path) and os.path.getsize(ogg_file_path) > 0:
            return ogg_file_path
        else:
            print(f"Ogg file {ogg_file_path} is not created properly")
            return
    except Exception as e:  # Catch any exception
        print(f"An error occurred: {e}")
        
# ibm_text_to_speech("Una farfalla curiosa danza tra le nuvole, mentre le stelle intrecciano un misterioso destino nel cielo notturno.", 0, '🇮🇹 Italian')