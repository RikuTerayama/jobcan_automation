# Note: render.yaml uses Docker mode, so this Procfile is NOT used
# Kept for backward compatibility if switching to native Python buildpack
web: gunicorn app:app --bind 0.0.0.0:$PORT --workers ${WEB_CONCURRENCY:-2} --threads ${WEB_THREADS:-2} --timeout ${WEB_TIMEOUT:-180} --graceful-timeout 30 --keep-alive 5 --max-requests 500 --max-requests-jitter 50 --access-logfile - --error-logfile - --log-level info 
