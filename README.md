# Smart Surveillance System For Public Mental Wellbeing

## Introduction
Previous works on smart surveillance systems often only focused on one task such as violence detection, and were heavyweight systems at the same time. This project aims to create a smart surveillacne system that does more than an average human (or a team of humans) could ever do.  

Not only will it help with regular surveillance related activities - such as violence and anomaly detection, it will also help provide valuable mental health related insights for data collected over a surveillance network.
The aim of this system is also to adapt to various environments and use cases, such as a classroom, mall, office, rehab centers and many more.

## Tech Stack
- Python version 3.11
- Node.js (Next.js) for the frontend
- Tensorflow
- OpenCV

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

## Methodology

Most existing smart surveillance systems rely on single modal data and focus on only one type of feature, such as facial expressions or crowd analysis.
Systems rarely used these models together, which causes the surveillance system to miss out on important details that could’ve been extracted if the system was trained to analyze all features from various modalities of data. 

The main challenge, however, is that each of the existing models such as facial emotion detection, crowd analysis and environmental factors detection models are usually heavyweight themselves, and would require a lot of resources if they had to run in a system together at all times.

Hence, we propose a smart surveillance system framework that integrates crowd emotion analysis, environmental context detection and anomaly recognition with crowd behavior analysis to estimate public mental health trends in real time and adapts based on the context of use, making it a suitable replacement for most traditional surveillance systems that currently exist.

![SystemArch](assets\systemarch.png)

### Details on backend ML services

1)	*Crowd Facial Emotion Detection Service*: This part of the system uses a trained ML model to look at people’s faces in a video through CCTV and finds out what emotions they are showing. 

2)	*Crowd Patterns and Behavior Service*: This service is responsible for providing insights on the crowd behavior, and to keep track of this behavior overtime in order to identify anomalies in the crowd. 

3)	*Body Posture and Language Service*: This service comprises of two trained ML models – the body posture analysis model and body language analysis model. 

4)	*Environmental Factors Analysis Service*: This service is responsible for analyzing images to extract key environmental factors and to monitor these conditions. 
