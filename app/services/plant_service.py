from sqlalchemy.orm import Session

from app.models import SolarPlant

_DEFAULT_PLANT_CODE = "DEFAULT"


def get_default_plant(db: Session) -> SolarPlant:
    plant = db.query(SolarPlant).filter(SolarPlant.plant_code == _DEFAULT_PLANT_CODE).first()
    if plant:
        return plant

    plant = SolarPlant(
        name="Default Plant",
        plant_code=_DEFAULT_PLANT_CODE,
        capacity_kw=3.0,
        location="Home",
        status="active",
    )
    db.add(plant)
    db.commit()
    db.refresh(plant)
    return plant


def get_user_plant(db: Session, username: str) -> SolarPlant:
    """Returns the plant owned by this user, or the shared default plant if they haven't set one up yet."""
    plant = db.query(SolarPlant).filter(SolarPlant.owner_username == username).order_by(SolarPlant.id).first()
    return plant or get_default_plant(db)
