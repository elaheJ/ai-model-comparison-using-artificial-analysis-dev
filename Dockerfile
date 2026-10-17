FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY model_compare ./model_compare
COPY python_app.py agent_app.py cloud_agent_app.py ./
COPY .streamlit/config.toml ./.streamlit/config.toml
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser
EXPOSE 8501
CMD ["python", "-m", "streamlit", "run", "python_app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
