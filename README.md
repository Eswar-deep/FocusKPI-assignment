# FDA Device Scraper API

This project provides a FastAPI endpoint to scrape the FDA's Total Product Life Cycle (TPLC) database for medical device problem data.

## Setup Instructions

Follow these steps to set up the project environment.

1.  **Clone the Repository**
    ```bash
    git clone <your-repository-url>
    cd FocusKPI-assignment
    ```

2.  **Create and Activate a Conda Environment**
    It is highly recommended to use a Conda environment to manage dependencies.
    ```bash
    # Create a new environment (e.g., named 'fda-scraper')
    conda create --name fda-scraper python=3.9

    # Activate the environment
    conda activate fda-scraper
    ```

3.  **Install Python Dependencies**
    Install the required Python packages using the `requirements.txt` file.
    ```bash
    pip install -r requirements.txt
    ```

## How to Run the App Locally

Once the setup is complete, you can run the FastAPI server using Uvicorn.

```bash
uvicorn main:app --reload
```

The server will start and be accessible at `http://localhost:8000`. The `--reload` flag enables hot-reloading, so the server will restart automatically when you make changes to the code.

## How to Test

The API provides a single endpoint, `/scrape`, which can be tested easily using the interactive Swagger UI documentation.

1.  With the server running, open your web browser and navigate to:
    `http://localhost:8000/docs`

2.  You will see the API documentation. Click on the `/scrape` endpoint to expand it.

3.  Click the "Try it out" button.

4.  Fill in the `device_name` field with an example search term like `syringe`. The `product_code` and `since` fields are optional.

5.  Click the "Execute" button. The API will perform the scrape (which may take a minute or two) and display the results in JSON format in the response body.
