# Docker-compose generator

## Structure
The compose generator is written in Python and requires additional packages. Therefore a virtual environment is used to run the script (utility for the virtual environment is `pipenv`).
There is a bash script which handles executing the generator-script in the virtual environment (including cleanup): It is located in the `docker/script` folder.

## Sequence of reading service files
The generator script always reads the basic service description file found in the `general` folder and adds or replaces values afterwards depending on the type of compose file to generate (script options provided as arguments).
The service description files will be read (and update/replace value) as the following sequence:
1. **Base** service description (contains CPU production description for Linux)<br>
`general` folder
1. **GPU training** service description<br>
`gpu` sub folder in `general` (optional / skipped when environment `initialization` selected)
1. **Environment** service description<br>
Sub folder (`dev`/`prod`/`init`) in `general`
1. **Host based** service descriptions<br>
Repeats steps 1 and 3 in another base folder (not `general`).
Currently only used for Windows hosts. 

## Compose manipulation in script
- Named volumes will be extracted by script and added automatically to the final compose file
- The port section rewrite for Windows Docker Toolbox is done within the script

## Assignment of services to environments
Assignment of services to environments (development, production, initialization) is done by constants defined at the top of the generator script (`generate_compose.py` in `docker/script`).

## Adding a service
Add a service by adding its name to the relevant constants in the generator script as described above. Then provide at least the basic service description file (`<name of service>.yml`) in the `general` folder (targeting Linux hosts for CPU production). If required add additional service description files for other environments (only containing modifications).
