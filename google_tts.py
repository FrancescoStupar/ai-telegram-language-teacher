import requests
import json
import base64
import os
from google.auth.transport.requests import Request
from google.oauth2 import service_account
import subprocess

def convert_mp3_to_ogg(mp3_file_path, ogg_file_path):
    command = ['ffmpeg', '-y', '-i', mp3_file_path, '-c:a', 'libopus', ogg_file_path]
    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, check=True)

language_to_voice = {
    '🇩🇪 German': {
        'languageCode': 'de-DE',
        'name': 'de-DE-Standard-C',
        'ssmlGender': 'FEMALE'
    },
    '🇵🇱 Polish': {
        'languageCode': 'pl-PL',
        'name': 'pl-PL-Wavenet-D',
        'ssmlGender': 'FEMALE'
    },
    '🇪🇸 Spanish': {
        'languageCode': 'es-ES',
        'name': 'es-ES-Standard-C',
        'ssmlGender': 'FEMALE'
    },
    '🇮🇹 Italian': {
        'languageCode': 'it-IT',
        'name': 'it-IT-Standard-B',
        'ssmlGender': 'FEMALE'
    },
    '🇫🇷 French': {
        'languageCode': 'fr-FR',
        'name': 'fr-FR-Standard-A',
        'ssmlGender': 'FEMALE'
    },
    '🇧🇷 Portuguese': {
        'languageCode': 'pt-BR',
        'name': 'pt-BR-Standard-C',
        'ssmlGender': 'FEMALE'
    },
    '🇮🇳 Hindi': {
        'languageCode': 'hi-IN',
        'name': 'hi-IN-Neural2-D',
        'ssmlGender': 'FEMALE'
    },
    '🇳🇱 Dutch': {
        'languageCode': 'nl-NL',
        'name': 'nl-NL-Standard-A',
        'ssmlGender': 'FEMALE'
    },
    '🇨🇳 Chinese': {
        'languageCode': 'cmn-CN',
        'name': 'cmn-CN-Wavenet-D',
        'ssmlGender': 'FEMALE'
    },
}

def google_text_to_speech(text, chat_id, selected_language):
    ogg_file_path = None
    try:
        print("google_text_to_speech function has been called")

        mp3_file_path = f"{chat_id}_response.mp3"
        ogg_file_path = f"{chat_id}_response.ogg"

        # Load the credentials from the service account key file
        creds = service_account.Credentials.from_service_account_file('google_tts.json')

        if creds.requires_scopes:
            creds = creds.with_scopes(['https://www.googleapis.com/auth/cloud-platform'])

        # Obtain an access token to use in the Authorization header of the API request
        auth_req = Request()
        creds.refresh(auth_req)
        access_token = creds.token

        headers = {
            'Authorization': 'Bearer ' + access_token,
            'Content-Type': 'application/json; charset=utf-8'
        }
        
        voice = language_to_voice[selected_language]  # Get the voice settings for the selected language

        data = {
            "input": {"text": text},
            "voice": voice,
            "audioConfig": {"audioEncoding": "MP3"}
        }

        response = requests.post('https://texttospeech.googleapis.com/v1/text:synthesize', 
                                 headers=headers, 
                                 data=json.dumps(data))

        if response.status_code == 200:
            print("TTS API call was successful")
            audio_content = json.loads(response.text)['audioContent']
            audio_bytes = base64.b64decode(audio_content)

            with open(mp3_file_path, "wb") as output_file:
                output_file.write(audio_bytes)
                print("MP3 file written successfully")

            convert_mp3_to_ogg(mp3_file_path, ogg_file_path)
            print("OGG file written successfully")
            try:
                os.remove(mp3_file_path)  # delete response audio file
            except Exception as e:
                print(f"Error occurred while trying to delete response audio file: {e}")

        else:
            print(f"TTS API call failed with status code {response.status_code}. Reason: {response.text}")
            ogg_file_path = None

    except Exception as e:  # Catch any exception
        print(f"An error occurred: {e}")
        ogg_file_path = None

    return ogg_file_path

# google_text_to_speech("Una farfalla curiosa danza tra le nuvole, mentre le stelle intrecciano un misterioso destino nel cielo notturno.", 0, '🇮🇹 Italian')