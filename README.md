# Post Quantum IoT Gateway with Trust and Drift Analytics

## Overview
This project is developed as a final year Computer Science and Engineering major project. It focuses on designing and implementing a secure, quantum resilient IoT communication system that addresses both classical and emerging quantum threats. The system combines post quantum cryptography with real time behavioral analysis to ensure secure and trustworthy IoT operations.

## Problem Statement
Current IoT systems rely on classical cryptographic schemes such as RSA and ECC, which are vulnerable to quantum attacks using algorithms like Shor’s algorithm. In addition to this, IoT environments are also exposed to classical threats such as unauthorized access, data tampering, and compromised sensors. Another major challenge is the lack of real time mechanisms to detect anomalies or drift in sensor data, which may indicate malicious activity or system failure.

## Objectives
- Design a quantum resilient communication framework for IoT systems  
- Integrate NIST standardized post quantum cryptographic algorithms  
- Enable secure key exchange, authentication, and data transmission  
- Detect anomalies and drift in sensor data in real time  
- Build a scalable and efficient edge gateway architecture  
- Provide a monitoring interface for system observability and alerts  

## Proposed Solution
The proposed solution is a Post Quantum IoT Gateway that integrates cryptographic security with behavioral monitoring. The system replaces traditional encryption mechanisms with lattice based post quantum schemes such as Kyber for key encapsulation and Dilithium for digital signatures.

The gateway is designed using C++ for performance efficiency and handles secure communication between IoT devices using TCP and UDP protocols. Alongside cryptographic protection, the system incorporates a drift analysis module to monitor sensor behavior and detect anomalies in real time.

## Drift Analysis and Anomaly Detection
The system includes a drift detection module that continuously analyzes incoming telemetry data from IoT sensors. Statistical techniques are used to identify deviations from expected patterns.

Key aspects include:
- Real time monitoring of sensor streams  
- Detection of anomalous patterns indicating compromised devices  
- Identification of data drift caused by environmental or malicious factors  
- Triggering alerts for abnormal system behavior  

This dual layer approach ensures both cryptographic security and behavioral trust in the system.

## Technologies, Frameworks and Tools

### Programming and Systems
- C++ for gateway and networking implementation  
- TCP and UDP socket programming for communication  

### Cryptography
- liboqs for integration of post quantum cryptographic algorithms  
- NIST PQC standards including Kyber and Dilithium  

### Frontend and Visualization
- Next.js for dashboard development  
- WebSockets for real time communication  

### Data Processing and Analysis
- Statistical methods for drift detection  
- Real time telemetry processing  

### Development Tools
- Git and GitHub for version control  
- Linux environment for development and testing  

## Architecture and Workflow

### System Architecture
The system consists of three main layers:

1. IoT Device Layer  
Simulated or real sensors generate telemetry data and send it to the gateway.

2. Edge Gateway Layer  
Handles secure communication using PQC algorithms  
Processes incoming data streams  
Performs drift detection and anomaly analysis  

3. Monitoring and Visualization Layer  
Displays real time data through a dashboard  
Provides alerts for anomalies and security events  

### Workflow
1. IoT devices generate data and initiate communication  
2. Secure key exchange is performed using Kyber  
3. Data is authenticated using Dilithium signatures  
4. Data is transmitted to the gateway via sockets  
5. Gateway processes data and performs drift analysis  
6. Results are sent to the dashboard via WebSockets  
7. Alerts are generated if anomalies are detected  

### Key Research Areas Relevant to This Project

- Quantum Safe Cryptography  
  Focus on designing cryptographic primitives secure against quantum adversaries  

- Applied Cryptography and Provable Security  
  Emphasis on formal security guarantees with practical efficiency  

- Secure Search over Encrypted Data  
  Techniques for querying encrypted data without exposing sensitive information  

## References and Resources

### Standards and Documentation
- NIST Post Quantum Cryptography Project  
  https://csrc.nist.gov/projects/post-quantum-cryptography  

- liboqs Documentation  
  https://openquantumsafe.org  

### Research Papers
- CRYSTALS Kyber Algorithm Specification  
  https://pq-crystals.org/kyber/  

- CRYSTALS Dilithium Algorithm Specification  
  https://pq-crystals.org/dilithium/  

- Harvest Now Decrypt Later Threat Analysis  
  https://www.mdpi.com  

- Multi-splitting Forking Based Modular Security of Signature Schemes in MQ Setting  
  https://www.researchgate.net/profile/Sanjit-Chatterjee  

- Revisiting the Security of Salted UOV Signature  
  https://www.researchgate.net/profile/Sanjit-Chatterjee  

- Identity Based Signature in Multivariate Quadratic Setting  
  https://www.researchgate.net/profile/Sanjit-Chatterjee  

- Secure and Efficient Wildcard Search over Encrypted Data  
  https://www.researchgate.net/profile/Sanjit-Chatterjee  

### Books and Academic Resources

- Identity Based Encryption by Sanjit Chatterjee and Palash Sarkar  
- Introduction to Modern Cryptography by Jonathan Katz and Yehuda Lindell  
- Post Quantum Cryptography by Daniel J Bernstein, Johannes Buchmann, Erik Dahmen  


### Standards and Open Source Resources

- NIST Post Quantum Cryptography Project  
  https://csrc.nist.gov/projects/post-quantum-cryptography  

- Open Quantum Safe liboqs  
  https://openquantumsafe.org  

- CRYSTALS Kyber  
  https://pq-crystals.org/kyber/  

- CRYSTALS Dilithium  
  https://pq-crystals.org/dilithium/  

## Conclusion
This project presents a practical implementation of a secure IoT gateway that combines post quantum cryptography with real time drift analytics. It demonstrates how future ready cryptographic systems can be integrated into real world architectures while maintaining efficiency and observability. The work aims to bridge the gap between theoretical PQC research and practical system level deployment.
