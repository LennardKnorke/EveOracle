# /backend/app/routers/dataset.py

import os
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Header, Cookie, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.database import UserAccount, get_db
from app.services.esi_api_interface import ESIPhone, ZkillPhone, ESI_Phone
from app.services.data_builder import DataBuilder, dataset_dir
from app.routers.auth import get_valid_access_token



router = APIRouter()



@router.get("/dataset/get_datasets")
async def get_all_datasets(access_token : str = Depends(get_valid_access_token)):
    """
    Will return a dictionaire of all the datasets created with the configurations
    """
    paths = os.listdir(dataset_dir)
    paths = [path for path in paths if os.path.isdir(path)]

    
    return {}


@router.post("/dataset/create_dataset")
async def create_dataset(
    max_time : float = 60.0,
    max_distance : float = 10_000.0,
    team_size : int = 2,
    permute_data : list[str]|None = None,
    synthetic_data : list[str]|None = None,
    session: str = Cookie(None, alias="session"),
    access_token : str = Depends(get_valid_access_token)
):
    """
    Will run the Dataset creation loop with the given settings.
    """
    # Pre Checks

    # Run Module
    builder = DataBuilder(max_time, max_distance, team_size, permute_data, synthetic_data)
    success, msg = builder.create()
    key = "success" if success else "error"
    return {key : msg}
