import random 
import logging
from typing import Optional
import redis 
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

#Configuration 


REDIS_URL="redis://172.27.93.89:6380/0"
GATEWAYS=["flutterwave","paystack","monnify"]

SUCCESS_STATUSES ={"CHARGED","AUTHORIZED","VBV_SUCCESSFUL"}

logging.basicConfig(level=logging.INFO)
LOGGER= logging.getLogger("routiq.mab")

app = FastAPI(title="RoutIQ MAB Server")
redis_client=redis.from_url(REDIS_URL, decode_responses=True)


#models

class PaymentInfo(BaseModel):
    paymentId:str
    amount:int
    currency:str
    paymentType:str
    paymentMethodType:str
    paymentMethod:str
    cardIsin:Optional[str]= None
    metadata:Optional[str]= None


class DecideGatewayRequest(BaseModel):
    