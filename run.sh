#!/bin/bash

MODE=$1
FILE=$2

if [ "$MODE" == "" ]; then
  MODE="0"
fi

if [ "$MODE" == "2" ] && [ "$FILE" == "" ]; then
  echo "❗ replay 모드(2)에서는 CSV 파일 경로를 지정하세요"
  echo "예: ./run.sh 2 logs/logged_20250702.csv"
  exit 1
fi

python entry.py "$MODE" "$FILE"
