# Smart Surveillance System For Public Mental Wellbeing

## Introduction
Previous works on smart surveillance systems often only focused on one task such as violence detection, and were heavyweight systems at the same time. This project aims to create a smart surveillacne system that does more than an average human (or a team of humans) could ever do.  

Not only will it help with regular surveillance related activities - such as violence and anomaly detection, it will also help provide valuable mental health related insights for data collected over a surveillance network.
The project is also designed in a way that it can adapt to various environments and use cases, such as a classroom, mall, office, rehab centers and many more.

## Project Setup

1) Go to your terminal and clone the repository using the `git clone` command. 

```
git clone https://github.com/keerthanar09/smart-surveillance-ndf.git
```
2) Open the project in your preffered text editor, and in the first terminal, change directory to `frontend` and install all necessary dependancies for the `next.js` frontend app.

```
cd frontend
npm install
```
3) Start the `next.js` app using the following command: 

```
npm run dev
```
This command is for production. Otherwise, run `npm start`.

4) Create python virtual environment for the entire project, body_service, crowd_service and emotion_service, and install the necessary requirements for each service, provided in a `requirements.txt` file within each respective folder.

```
# New terminal at root of project directory (at smart-surveillance-ndf)
py -3.11 -m venv venv
venv/Scripts/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

# Terminal 2
cd crowd_service
py -3.11 -m venv crowd_venv
crowd_venv\Scripts\activate
pip install -r requirements.txt

# Do the same as above for the body_service and emotion_service.

```


5) Now, we need to run each of the services. The plan is to dockerize each service and use them as a microservice, but since this system is still being developed, docker hasn't been used yet. So each service will be individually run as follows (open a new terminal for each service):

```
//Terminal 2
cd crowd_service
crowd_venv\Scripts\activate
uvicorn crowd_analyser:app --host 127.0.0.1 --port 8100   

//Terminal 3
venv\Scripts\activate
cd orchestrator
uvicorn app:app --host 127.0.0.1 --port 8000 --reload   

//Terminal 4
venv\Scripts\activate
cd env_service
uvicorn envir_analyzer:app --host 127.0.0.1 --port 8200 --reload       

//Terminal 5
cd emotion_service
emovenv\Scripts\activate
uvicorn emo_analyzer:app --host 127.0.0.1 --port 8300 --reload      

//Terminal 6
cd body_service
bodyvenv\Scripts\activate
uvicorn body_analyzer:app --host 127.0.0.1 --port 8400 --reload      

```

*Note: This set-up is purely for development purposes.*

5) Create a `.env` file in the project root and add a variable named `GEMINI_API_KEY`, and provide your API key as it's value. This API key can be obtained from [Google Cloud Console](https://console.cloud.google.com/). Enable *Gemini API* and create an API key under **API and Credentials**. *Future me: Removed gemini API temporarily since the performance overhead is more than desired. But, planning to add it later again for weekly or monthly reports.*

*For more details on the project, refer to report.pdf present in this folder.*
