import hmac
import os
from fastapi import Depends, FastAPI, Header, HTTPException
from typing import Optional
from . import database, models, schemas
from sqlalchemy.orm import Session
from datetime import datetime

app = FastAPI(title="Vinyl API (dev)")


def require_api_key(authorization: Optional[str] = Header(default=None)) -> None:
    """Require the configured bearer key while allowing keyless local use."""
    expected_key = os.environ.get("VINYL_API_KEY")
    if not expected_key:
        return

    scheme, _, supplied_key = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not hmac.compare_digest(supplied_key, expected_key):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "Bearer"},
        )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.on_event("startup")
def on_startup():
    database.init_db()


@app.post("/listings/bulk", dependencies=[Depends(require_api_key)])
def post_listings_bulk(payload: schemas.BulkListings):
    """Accept bulk listings for a release and persist them.

    This endpoint enforces `BulkListings` validation via Pydantic. Extra fields
    in the request will return a 422. Use this strict validation for data
    integrity; update clients to match the schema.
    """
    db: Session = database.SessionLocal()
    saved = 0
    try:
        for lst in payload.listings:
            obj = models.Listing(
                listing_id=lst.listing_id,
                release_id=payload.release_id,
                price=lst.price,
                currency=lst.currency,
                condition=lst.condition,
                sleeve_condition=lst.sleeve_condition,
                ships_from=lst.ships_from,
                seller=lst.seller,
                listing_url=lst.listing_url,
                last_fetched=lst.last_fetched or datetime.utcnow(),
                price_usd=lst.price_usd,
                ships_to_us=lst.ships_to_us,
                shipping_notes=lst.shipping_notes,
            )
            db.add(obj)
            saved += 1
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        db.close()

    return {"saved": saved}


@app.post("/users/{user_id}/plays", dependencies=[Depends(require_api_key)])
def log_play(user_id: int, payload: schemas.PlayIn):
    """Log a play for a user.

    Payload: { release_id, played_at (optional ISO), source, notes }
    """
    db: Session = database.SessionLocal()
    try:
        played_at = payload.played_at or datetime.utcnow()
        obj = models.Play(
            user_id=user_id,
            release_id=payload.release_id,
            played_at=played_at,
            source=payload.source,
            notes=payload.notes,
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        db.close()

    return {"id": obj.id, "user_id": obj.user_id, "release_id": obj.release_id}
