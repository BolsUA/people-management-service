# Use an official Python runtime as the base image
FROM python:3.12-slim

RUN addgroup --system appgroup && adduser --system --group appuser

# Set the working directory
WORKDIR /people_management

RUN chown -R appuser:appgroup /people_management

# Copy the requirements file
COPY ./app ./app
COPY ./requirements.txt ./
COPY ./wait_for_db.py ./

# Expose the port FastAPI runs on
EXPOSE 8000

# Install dependencies
# RUN pip install --no-cache-dir -r requirements.txt
RUN pip install -r requirements.txt

USER appuser

CMD ["sh", "-c", "python3 wait_for_db.py && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
