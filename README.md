# Music Subscription Application – AWS Cloud Deployment

A cloud-based music subscription application developed using **Python, Flask and AWS**. The project explores three different cloud deployment architectures, demonstrating how application backends can be deployed and managed using AWS services.

The application supports user authentication, music browsing and subscription management, with data stored in Amazon DynamoDB and media assets hosted on Amazon S3.

## Project Overview

This project was developed to explore and compare three AWS deployment approaches:

1. **Amazon EC2** – Deploying a Flask application on a virtual machine.
2. **Amazon ECS with Fargate** – Containerising and deploying the application using Docker.
3. **Amazon API Gateway and AWS Lambda** – Implementing a serverless backend architecture.

Each implementation provides backend functionality for the music subscription application while using AWS services for storage, hosting and application deployment.

## Architecture & Technologies

| Component | AWS Service / Technology | Purpose |
|---|---|---|
| Frontend Hosting | Amazon S3 | Hosting frontend application files |
| Backend – EC2 | Amazon EC2 | Hosting Flask application |
| Backend – Containers | Amazon ECS Fargate | Running containerised backend |
| Backend – Serverless | API Gateway & AWS Lambda | Handling serverless API requests |
| Database | Amazon DynamoDB | Storing music and subscription information |
| Image Storage | Amazon S3 | Hosting music-related images |
| Container Registry | Amazon ECR | Storing Docker images |
| Backend Framework | Python & Flask | Application backend |
| Containerisation | Docker | Packaging the application |

## Deployment Architectures

### 1. EC2-Based Deployment

The first implementation uses an Amazon EC2 instance to host the Flask backend.

- Configured an EC2 instance to run the Flask application.
- Used Gunicorn as the WSGI application server.
- Configured the application to serve backend requests over HTTP.
- Connected the backend to Amazon DynamoDB and S3.

### 2. Container-Based Deployment – ECS Fargate

The second implementation explores container-based deployment using Docker and Amazon ECS.

- Created a Docker image of the Flask backend.
- Pushed the image to Amazon Elastic Container Registry (ECR).
- Deployed the container using Amazon ECS with Fargate.
- Configured the application to interact with the AWS database and storage services.

### 3. Serverless Deployment – API Gateway & Lambda

The third implementation uses a serverless architecture.

- Developed backend functionality using AWS Lambda.
- Configured API Gateway to expose backend endpoints.
- Integrated Lambda functions with Amazon DynamoDB.
- Explored event-driven execution without managing backend servers.

## Database Design

Amazon DynamoDB was used to manage music catalogue and subscription information.

**Music Table**

- Partition Key (PK): `artist`
- Sort Key (SK): `album#title`
- Global Secondary Index (GSI): `title` / `artist#album`
- Local Secondary Index (LSI): `artist` / `year#title`
- Included music metadata and image URLs.

**Subscription Table**

- Partition Key (PK): `email`
- Sort Key (SK): `artist#album#title`
- Local Secondary Index (LSI): `album#title`

The database design supports music catalogue queries and user-specific subscription records.

## Key Features

- User authentication and login functionality.
- Music catalogue browsing.
- Music subscription management.
- CRUD operations for application data.
- DynamoDB integration for persistent storage.
- S3 integration for frontend hosting and image storage.
- Multiple backend deployment architectures.

## Repository Structure

The repository contains separate implementations for the different deployment approaches.

```text
Music-Subscription-Application/
│
├── EC2/
│   ├── app.py
│   └── ...
│
├── ECS/
│   ├── Dockerfile
│   ├── app.py
│   └── ...
│
├── Lambda/
│   ├── ...
│
├── frontend/
│   └── ...
│
└── README.md
```

*Note: Adjust the folder names above to match the actual repository structure.*

## Learning Outcomes

Through this project, I gained practical experience in:

- Deploying Python web applications on AWS.
- Understanding server-based, container-based and serverless architectures.
- Building and deploying Docker containers.
- Working with Amazon DynamoDB and designing database indexes.
- Integrating AWS services through application backends.
- Exploring scalable cloud application deployment approaches.

## Future Improvements

- Implement automated CI/CD pipelines.
- Introduce improved authentication and authorisation.
- Add monitoring and logging using Amazon CloudWatch.
- Improve application scalability and fault tolerance.
- Implement automated infrastructure deployment using Infrastructure as Code.

## Technologies

`Python` `Flask` `AWS` `EC2` `ECS` `Fargate` `Lambda` `API Gateway` `DynamoDB` `S3` `ECR` `Docker` `Gunicorn`

---

**Developed as part of an RMIT University Cloud Computing project.**
