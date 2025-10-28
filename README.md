# Portable Joint Stiffness Quantification and Handgrip Assessment Unit
This project proposes a low-cost disease progression tracking system that measures stiffness in the Metacarpophalangeal (MCP) and Proximal Interphalangeal (PIP) joints and the ability of a patient to sustain grip - two key early indicators of RA. This system features a mechanical actuator that applies controlled angular flexion to the MCP joints at angles ranging from -30 ° to +60 ° and an FSR to measure the resistive force exerted by the finger on it, both of which will help measure the joint stiffness. The device will also have a load cell attached to a gripping unit that measures the force exerted on the load cell to calculate the grip strength.

---

The folder titled **Python Scripts** contains 4 codes:
1. **MAIN.py**: The entire code. Reading the sensor values from arduino and saving it to a .csv file, analysing the data, and GUI -all combined into a single script. If you want to try out our system, this is the code you should run.
2. **read_arduino**: Reads the data obtained from arduino code (sensor readings) and saves it into a .csv file.
3. **analysis.py** and **analysismore.py**: Analyses the data obtained and calculated important parameters like "peak strength", "time of sustained handgrip" etc. (analysismore.py contains more such parameters compared to analysis.py). 

---

The **Arduino Code** file contains the script for recording the sensor values from the FSR and Loadcell. 

---

There are two images, one is the circuit diagram of our system and the other is the reading obtained from a person who is known to have RA. The latter image shows our GUI.
