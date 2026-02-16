import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from sklearn.decomposition import PCA
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import (
    ClusterPoint,
    OpinionResponse,
    OpinionSubmit,
    OpinionWithDistance,
    QuestionResponse,
    SubmitResponse,
    SummaryResponse,
    VisualizationResponse,
)
from app.core.database import get_db
from app.services.ai import summarize_opinions
from app.services.opinions import (
    find_bridge_opinion,
    find_nearest_opinions,
    get_current_question,
    get_opinion_by_hash,
    get_opinions_for_question,
    submit_opinion,
)

router = APIRouter()


@router.get("/question/current", response_model=QuestionResponse)
async def current_question(db: AsyncSession = Depends(get_db)):
    question = await get_current_question(db)
    if not question:
        raise HTTPException(status_code=404, detail="No active question")
    return question


@router.post("/opinion", response_model=SubmitResponse)
async def post_opinion(body: OpinionSubmit, db: AsyncSession = Depends(get_db)):
    question = await get_current_question(db)
    if not question:
        raise HTTPException(status_code=404, detail="No active question")

    opinion = await submit_opinion(db, question.id, body.text, body.region)

    nearest = await find_nearest_opinions(
        db, list(opinion.embedding), question.id, opinion.hash, limit=5
    )
    bridge = await find_bridge_opinion(
        db, list(opinion.embedding), question.id, opinion.hash, opinion.region
    )

    return SubmitResponse(
        hash=opinion.hash,
        anonymized_text=opinion.anonymized_text,
        language=opinion.language,
        nearest=[
            OpinionWithDistance(
                hash=n.hash,
                anonymized_text=n.anonymized_text,
                region=n.region,
                trust_score=n.trust_score,
            )
            for n in nearest
        ],
        bridge=OpinionWithDistance(
            hash=bridge.hash,
            anonymized_text=bridge.anonymized_text,
            region=bridge.region,
            trust_score=bridge.trust_score,
        )
        if bridge
        else None,
    )


@router.get("/opinion/{opinion_hash}", response_model=OpinionResponse)
async def get_opinion(opinion_hash: str, db: AsyncSession = Depends(get_db)):
    opinion = await get_opinion_by_hash(db, opinion_hash)
    if not opinion:
        raise HTTPException(status_code=404, detail="Opinion not found")
    return OpinionResponse(
        hash=opinion.hash,
        anonymized_text=opinion.anonymized_text,
        language=opinion.language,
        region=opinion.region,
        trust_score=opinion.trust_score,
        created_at=opinion.created_at,
    )


@router.get("/opinions/current", response_model=VisualizationResponse)
async def current_opinions(db: AsyncSession = Depends(get_db)):
    question = await get_current_question(db)
    if not question:
        raise HTTPException(status_code=404, detail="No active question")

    opinions = await get_opinions_for_question(db, question.id)

    # Project embeddings to 2D for visualization using PCA
    points = []
    if len(opinions) >= 2:
        embeddings = np.array([list(o.embedding) for o in opinions if o.embedding is not None])
        if len(embeddings) >= 2:
            n_components = min(2, len(embeddings))
            pca = PCA(n_components=n_components)
            coords = pca.fit_transform(embeddings)
            for i, opinion in enumerate(opinions):
                if opinion.embedding is not None and i < len(coords):
                    points.append(
                        ClusterPoint(
                            hash=opinion.hash,
                            x=float(coords[i][0]),
                            y=float(coords[i][1]) if n_components == 2 else 0.0,
                            region=opinion.region,
                            text_preview=opinion.anonymized_text[:120],
                        )
                    )
    elif len(opinions) == 1:
        points.append(
            ClusterPoint(
                hash=opinions[0].hash,
                x=0.0,
                y=0.0,
                region=opinions[0].region,
                text_preview=opinions[0].anonymized_text[:120],
            )
        )

    return VisualizationResponse(
        question=QuestionResponse(
            id=question.id,
            text=question.text,
            slug=question.slug,
            created_at=question.created_at,
        ),
        points=points,
        total_opinions=len(opinions),
    )


@router.get("/opinions/current/summary", response_model=SummaryResponse)
async def current_summary(db: AsyncSession = Depends(get_db)):
    question = await get_current_question(db)
    if not question:
        raise HTTPException(status_code=404, detail="No active question")

    opinions = await get_opinions_for_question(db, question.id)
    if not opinions:
        raise HTTPException(status_code=404, detail="No opinions yet")

    texts = [o.anonymized_text for o in opinions]
    summary = await summarize_opinions(texts, question.text)

    return SummaryResponse(
        question=QuestionResponse(
            id=question.id,
            text=question.text,
            slug=question.slug,
            created_at=question.created_at,
        ),
        summary=summary,
        total_opinions=len(opinions),
    )


@router.get("/opinion/{opinion_hash}/bridge", response_model=OpinionWithDistance | None)
async def bridge_opinion(opinion_hash: str, db: AsyncSession = Depends(get_db)):
    opinion = await get_opinion_by_hash(db, opinion_hash)
    if not opinion:
        raise HTTPException(status_code=404, detail="Opinion not found")

    bridge = await find_bridge_opinion(
        db, list(opinion.embedding), opinion.question_id, opinion.hash, opinion.region
    )
    if not bridge:
        return None
    return OpinionWithDistance(
        hash=bridge.hash,
        anonymized_text=bridge.anonymized_text,
        region=bridge.region,
        trust_score=bridge.trust_score,
    )
