from functools import partial

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.auth import get_current_buyer, get_current_admin
from app.db_depends import get_async_db
from app.schemas import Review as ReviewSchema, ReviewCreate
from app.models.reviews import Review as ReviewModel
from app.routers.products import router as product_router
from app.models.products import Product as ProductModel
from app.models.users import User as UserModel

router = APIRouter(
    prefix="/reviews",
    tags=["reviews"],
)

@router.get("/", response_model=list[ReviewSchema])
async def get_all_reviews(db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список всех отзывов.
    """
    stmt = select(ReviewModel).where(ReviewModel.is_active == True)
    result = await (db.scalars(stmt))
    reviews = result.all()
    return reviews

@product_router.get("/{product_id}/reviews", response_model=list[ReviewSchema])
async def get_reviews_by_product(product_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список отзывов об указанном товаре по его ID.
    """
    stmt = select(ProductModel).where(ProductModel.id == product_id,
                                       ProductModel.is_active == True)
    result = await (db.scalars(stmt))
    db_category = result.first()
    if db_category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    reviews_stmt = select(ReviewModel).where(ReviewModel.product_id == product_id,
                                      ReviewModel.is_active == True).order_by(ReviewModel.comment_date.desc())
    result = await (db.scalars(reviews_stmt))
    reviews = result.all()
    return reviews

async def update_product_rating(db: AsyncSession, product_id: int):
    result = await db.execute(
        select(func.avg(ReviewModel.grade)).where(
            ReviewModel.product_id == product_id,
            ReviewModel.is_active == True
        )
    )
    avg_rating = result.scalar() or 0.0
    product = await db.get(ProductModel, product_id)
    product.rating = avg_rating
    await db.commit()


@router.post("/", response_model=ReviewSchema, status_code=status.HTTP_201_CREATED)
async def create_review(
        review: ReviewCreate,
        db: AsyncSession = Depends(get_async_db),
        current_user: UserModel = Depends(get_current_buyer)
):
    """
    Создаёт новый отзыв для товара (только для 'buyer').
    """
    stmt = select(ProductModel).where(
        ProductModel.id == review.product_id,
        ProductModel.is_active == True)
    result = await (db.scalars(stmt))
    product = result.first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product not found")
    db_review = ReviewModel(**review.model_dump(), user_id=current_user.id)
    db.add(db_review)
    await db.commit()
    await update_product_rating(db, product.id)
    await db.refresh(db_review)     # Для получения id и is_active из базы
    return db_review

@router.delete("/{review_id}", response_model=ReviewSchema)
async def delete_review(
        review_id: int,
        db: AsyncSession = Depends(get_async_db),
        current_user: UserModel = Depends(get_current_admin)
):
    """
    Удаляет отзыв по его ID.
    """
    stmt = select(ReviewModel).where(ReviewModel.id == review_id, ReviewModel.is_active == True)
    result = await (db.scalars(stmt))
    review = result.first()
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    await db.execute(update(ReviewModel).where(ReviewModel.id == review_id).values(is_active=False))
    await db.commit()
    await update_product_rating(db, review.product_id)
    await db.refresh(review)
    return review
