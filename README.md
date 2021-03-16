<div align="center">
  <a href="https://projects.tib.eu/en/viva/projekt/">
    <img src="img/viva-logo-blue.png" alt="VIVA">
  </a>
</div>

VIVA is a software tool for building content-based retrieval methods for video archives based on deep learning models. The tool enables visual information retrieval through concept classification and person identification. It allows to easily train models from scratch and adjust them by adding new people or concepts. To reduce the manual effort of collecting training samples, the workflow includes a web crawler, image similarity search, as well as review and user feedback components.

Funded by the German Research Foundation (DFG), the VIVA software was developed at the Department of Distributed Computing (University of Marburg) and the Visual Analytics group (Leibniz Information Centre for Technology and Natural Sciences - TIB) in cooperation with the German Broadcasting Archive (DRA).

# Quick start 

*For a detailed documentation see [wiki](https://github.com/umr-ds/VIVA/wiki/)*

* Software requirements: `docker`, `docker-compose`, `pipenv` (for compose generator)

* Create data folders
  ```
  cd `docker/script/
   ./create_data_folders.sh
  ```
* (Optional) Add Elastic Search index to `docker/data/elasticsearch`
  ```
  chown -R 1000 elasticsearch
  ```
  See [wiki](https://github.com/umr-ds/VIVA/wiki/Similarity-search) for details.
  
* Download the required face processing models (see [wiki](https://github.com/umr-ds/VIVA/wiki/Face-processing)).

* Set the file permissions of `redis.conf`: `chmod o+r docker/build/redis/redis.conf`.

* (Optional) Modify `.env` inside the `docker` folder eg. to set up custom ports and a custom media folder location

* Initialize database
  `cd docker`
   1. Create schema
      ```bash
      bash script/generate_compose.sh -i
      docker-compose up --abort-on-container-exit
      ```
   2. Import default values and initialize sequences:
      ```bash
      ./script/run_sql_script.sh sql/base_init.sql
      ```
   3. Import development users example to get access to the app (username `test` and password `nix`)
      ```bash
      ./script/run_sql_script.sh sql/users_development.sql
      ```
   *Hint:* If you want to reinitialize the database make sure to delete the folder `docker/data/postgres/data` otherwise initialization routine of PostgreSQL will not be executed.

* (Optional) Import sample data set


* Select the docker-compose environment
   ```bash
   bash script/generate_compose.sh -d django        # development (Django) on CPU
   bash script/generate_compose.sh -d django -t gpu # development (Django) on GPU
   bash script/generate_compose.sh -d keras         # development (Keras) on CPU
   bash script/generate_compose.sh -d keras -t gpu  # development (Keras) on GPU
   ```
  Start Docker containers
   ```bash
   docker-compose up
   ```

_For development:_
Open the *app* project in an IDE and start the Django development server (e.g in [PyCharm Professional](https://github.com/umr-ds/VIVA-Tool/wiki/IDE-configuration-%28Pycharm%29)). Go to http://localhost:8000/ and log in.

# Sample datasets

Datasets should contain database information and the corresponding media files. When importing your own media files please make sure to also import corresponding database information according to our [database structure](https://github.com/umr-ds/VIVA/face-processing/wiki/Database).

## How to import data sets

_Note_: Make sure when executing the following commands that the working directory is set to `docker` folder!

After setting up the docker compose environment datasets can be imported. Database information can be imported in different ways:

* A sql file containing all required information without the need of additional files: Regardless of the location of the sql file the following command can be executed.
   ```bash
   ./script/run_sql_script.sh PATH_TO_SQL_FILE
   ```

* Multiple files that depend on each other: Copy all files to `docker/data/postgres/transfer`. To execute a sql file in the transfer folder use:
   ```bash
   ./script/run_transfer_sql_script.sh FILENAME_OF_SQL_FILE  # no path allowed here
   ```

* To execute a custom command in the transfer path (above), ensure that the database container is running and execute:
   ```bash
   docker exec -it -w "/transfer" "$(docker-compose ps -q db)" COMMAND
   ```

### Additional notes

* When importing a dataset that also contains media files make sure to add the media files to corresponding folder (`app/media` folder or custom location).

* Serving media files in production environment requires the folders and files to be world readable including the folder provided in the `docker/.env` file. If you do not want them to be world readable the folders and files have to be owned by the user with id 101 (Nginx daemon).

* Datasets could interfere with each other (violating constraints in database).

## What we provide
There is a sample database that contains some concepts but no media. The database information can be found in `docker/sql/sample_concepts.sql`.
Currently we are working on a larger sample media dataset. Stay tuned!
