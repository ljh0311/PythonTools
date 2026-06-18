#!/bin/sh
set -e

cd /app

case "${1:-recommend}" in
  recommend)
    shift
    exec python run_recommendations.py "$@"
    ;;
  clean)
    shift
    exec python run_cleaning_pipeline.py "$@"
    ;;
  shell)
    exec sh
    ;;
  *)
    exec "$@"
    ;;
esac
