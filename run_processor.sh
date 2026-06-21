#!/bin/bash
# Ejecuta el procesador de tickets

export $(cat /home/rodri/.openclaw/workspace/ticket-processor/.env | xargs)

cd /home/rodri/.openclaw/workspace/ticket-processor

python3 ticket_processor.py