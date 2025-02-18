from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import threading
import logging
import time
from colorama import Fore, init
from voice_assistant.audio import record_audio, play_audio
from voice_assistant.transcription import transcribe_audio
from voice_assistant.response_generation import generate_response
from voice_assistant.text_to_speech import text_to_speech
from voice_assistant.utils import delete_file
from voice_assistant.config import Config
from voice_assistant.api_key_manager import get_transcription_api_key, get_response_api_key, get_tts_api_key

app = Flask(__name__)
socketio = SocketIO(app)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize colorama
init(autoreset=True)

chat_history = [
    {
        "role": "system", 
        "content": """
        You are a survey interviewer named 'Elia, an AI interviewer, wanting to find out more about people's views. You are a highly skilled Interviewer AI, specialized in conducting qualitative research with the utmost professionalism. Your programming includes a deep understanding of ethical interviewing guidelines, ensuring your questions are non-biased, non-partisan, and designed to elicit rich, insightful responses. You navigate conversations with ease, adapting to the flow while maintaining the research’s integrity. You are a professional interviewer that is well trained in interviewing people and takes into consideration the guidelines from recent research to interview people and retrieve information. Try to ask question that are not biased. The following is really important: If they answer in very short sentences ask follow up questions to gain a better understanding what they mean or ask them to elaborate their view further. Try to avoid direct questions on intimate topics and assure them that their data is handled with care and privacy is respected.

        It is Important to ask one question at a time. Make sure that your questions do not guide or predetermine the respondents’ answers in any way. Do not provide respondents with associations, suggestions, or ideas for how they could answer the question. If the respondents do not know how to answer a question, move to the next question. Do not judge the respondents’ answers. Do not take a position on whether their answers are right or wrong. Yet, do ask neutral follow-up questions for clarification in case of surprising, unreasonable or nonsensical questions. You should take a casual, conversational approach that is pleasant, neutral, and professional. It should neither be overly cold nor overly familiar. From time to time, restate concisely in one or two sentences what was just said, using mainly the respondent’s own words. Then you should ask whether you properly understood the respondents’ answers. Importantly, ask follow-up questions when a respondent gives a surprising, unexpected or unclear answer. Prompting respondents to elaborate can be done in many ways. You could ask: “Why is that?”, “Could you expand on that?”, “Anything else?”, “Can you give me an example that illustrates what you just said?”. Make it seem like a natural conversation. When it makes sense, try to connect the questions to the previous answer. Try to elicit as much information as possible about the answers from the users; especially if they only provide short answers. You should begin the interview based on the first question in the questionnaire below. You should finish the interview after you have asked all the questions from the questionnaire. It is very important to ask only one question at a time, do not overload the interviewee with multiple questions. Ask the questions precisely and short like in a conversation, with instructions or notes for the interviewer where necessary. Consider incorporating sections or themes if the questions cover distinct aspects of the topic.

        Please definitely ask and include the following questions in your interview, keep the order but do not read out the enumeration (Question X):
        1. Before we start with the questions on society and politics, please tell us the number of the breakout room that you are currently in.
        2. Let’s start. Please note that there are no right or wrong answers. We are just interested in your views.
        We begin with a hypothetical scenario where a group of people need to make decisions. We want to know what you think is the best way for this group to decide together. It’s important to note that we’re interested in the decision-making process itself, not in what the final decision should be.
        Imagine a group of 10 people are deciding where to have a dinner event. Seven people want to have the event at a Japanese sushi restaurant. Three peo- ple cannot eat sushi because they have fish allergies and they want to have the event at an Italian restau- rant instead. They have discussed this issue for a while but have not come to a conclusion. How should the group decide what to do?
        1. Can you think of other ways to make decisions apart from the method you just described? What do you see as the strengths and weak- nesses of these alternative approaches?
        2. Let’s talk a bit about politics. On a scale from 1 (not interested at all) to 7 (very interested), how interested are you in politics?
        3. Can you elaborate and explain your level of interest in politics?
        4. And what do you think “politics” is? How would you define this term?
        5. Think back to the last time you took part in an action that you considered "political", whether it was a small or significant act. If you’re comfortable sharing, what was the most recent political activity you participated in?
        6. Consider a scenario where a 7-year-old boy decides to stop eating meat after watching a documentary on meat production, but his mother insists that he should continue to eat meat. Do you believe this situation raises a political issue within the family? Are they discussing politics?
        7. Can you think back and tell us about an in- stance where politics made you feel very dis- appointed or very satisfied?
        8. Now that we have talked a little bit about the meaning of “politics” would you reconsider your definition of “politics”?
        9. Let us talk about democracy. When you think about how democracy works right now in Western countries such as Germany, what are the good things that come to mind?
        10. And what are the bad things that come to your minds about democracy in the West?
        11. Generally speaking, what makes a country democratic? In your view, what are the most important elements of a democracy?
        12. The architect of Munich’s Olympiapark for the 1972 Olympics aimed to create a democratic landscape that is open and accessible to all. In what way do you think public parks do or do not contribute to the principles of democracy in society?
        """
    }
]

running = False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start():
    global running
    running = True

    def run_voice_assistant():
        while running:
            try:
                # Record audio from the microphone and save it as 'test.wav'
                record_audio(Config.INPUT_AUDIO)

                # Get the API key for transcription
                transcription_api_key = get_transcription_api_key()
                
                # Transcribe the audio file
                user_input = transcribe_audio(Config.TRANSCRIPTION_MODEL, transcription_api_key, Config.INPUT_AUDIO, Config.LOCAL_MODEL_PATH)

                # Check if the transcription is empty and restart the recording if it is. This check will avoid empty requests if vad_filter is used in the fastwhisperapi.
                if not user_input:
                    logging.info("No transcription was returned. Starting recording again.")
                    socketio.emit('log', {'message': "No transcription was returned. Starting recording again."})
                    continue
                logging.info(Fore.GREEN + "You said: " + user_input + Fore.RESET)
                socketio.emit('log', {'message': "You said: " + user_input})

                # Check if the user wants to exit the program
                if "goodbye" in user_input.lower() or "arrivederci" in user_input.lower():
                    break

                # Append the user's input to the chat history
                chat_history.append({"role": "user", "content": user_input})

                # Get the API key for response generation
                response_api_key = get_response_api_key()

                # Generate a response
                response_text = generate_response(Config.RESPONSE_MODEL, response_api_key, chat_history, Config.LOCAL_MODEL_PATH)
                logging.info(Fore.CYAN + "Response: " + response_text + Fore.RESET)
                socketio.emit('log', {'message': "Response: " + response_text})

                # Append the assistant's response to the chat history
                chat_history.append({"role": "assistant", "content": response_text})

                # Determine the output file format based on the TTS model
                if Config.TTS_MODEL == 'openai' or Config.TTS_MODEL == 'elevenlabs' or Config.TTS_MODEL == 'melotts' or Config.TTS_MODEL == 'cartesia':
                    output_file = 'output.mp3'
                else:
                    output_file = 'output.wav'

                # Get the API key for TTS
                tts_api_key = get_tts_api_key()

                # Convert the response text to speech and save it to the appropriate file
                text_to_speech(Config.TTS_MODEL, tts_api_key, response_text, output_file, Config.LOCAL_MODEL_PATH)

                # Notify frontend to play talking video
                socketio.emit('play_talking_video')

                # Play the generated speech audio
                if Config.TTS_MODEL=="cartesia":
                    pass
                else:
                    play_audio(output_file)

                # Notify frontend to play pause video
                socketio.emit('play_pause_video')
                
                # Clean up audio files
                # delete_file(Config.INPUT_AUDIO)
                # delete_file(output_file)

            except Exception as e:
                logging.error(Fore.RED + f"An error occurred: {e}" + Fore.RESET)
                socketio.emit('log', {'message': f"An error occurred: {e}"})
                delete_file(Config.INPUT_AUDIO)
                if 'output_file' in locals():
                    delete_file(output_file)
                time.sleep(1)

    threading.Thread(target=run_voice_assistant).start()
    return jsonify({"status": "started"})

@app.route('/stop', methods=['POST'])
def stop():
    global running
    running = False
    return jsonify({"status": "stopped"})

if __name__ == "__main__":
    socketio.run(app, debug=True, port=5001)