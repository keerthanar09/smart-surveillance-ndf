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

4) Now, we need to run each of the services. The plan is to dockerize each service and use them as a microservice, but since this system is still being developed, docker hasn't been used yet. So each service will be individually run as follows (open a new terminal for each service):

```
//Terminal 2
cd crowd_service
uvicorn crowd_analyser:app --host 127.0.0.1 --port 8100   

//Terminal 3
cd orchestrator
uvicorn app:app --host 127.0.0.1 --port 8000 --reload   

//Terminal 4
cd env_service
uvicorn envir_analyzer:app --host 127.0.0.1 --port 8200 --reload       

//Terminal 5
cd emotion_service
uvicorn emo_analyzer:app --host 127.0.0.1 --port 8300 --reload      

//Terminal 6
cd body_service

```

*Note: This set-up is purely for development purposes.*

5) Create a `.env` file in the project root and add a variable named `GEMINI_API_KEY`, and provide your API key as it's value. This API key can be obtained from [Google Cloud Console](https://console.cloud.google.com/). Enable *Gemini API* and create an API key under **API and Credentials**

## Project Structure

## Features

## Collaborators and Contacts

## Relevant Links
