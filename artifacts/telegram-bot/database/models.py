from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str] = mapped_column(String(128), nullable=False)
    last_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    points: Mapped[int] = mapped_column(Integer, default=0)
    referred_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    free_installs: Mapped[int] = mapped_column(Integer, default=0)
    discount_pct: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    bots: Mapped[list["Bot"]] = relationship("Bot", back_populates="owner")
    coupon_uses: Mapped[list["CouponUse"]] = relationship("CouponUse", back_populates="user")

    def __repr__(self) -> str:
        return f"<User id={self.id} tg={self.telegram_id}>"


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    max_bots: Mapped[int] = mapped_column(Integer, default=1)
    max_plugins: Mapped[int] = mapped_column(Integer, default=3)
    price: Mapped[float] = mapped_column(Float, default=0.0)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def __repr__(self) -> str:
        return f"<Plan id={self.id} name={self.name}>"


class Bot(Base):
    __tablename__ = "bots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    token_hint: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_running: Mapped[bool] = mapped_column(Boolean, default=False)
    mode: Mapped[str] = mapped_column(String(16), default="studio")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    owner: Mapped["User"] = relationship("User", back_populates="bots")

    def __repr__(self) -> str:
        return f"<Bot id={self.id} name={self.name}>"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admin_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, default=None)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} admin={self.admin_id} action={self.action}>"


class Coupon(Base):
    __tablename__ = "coupons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)

    # Type: "seeds" | "free_install" | "discount"
    type: Mapped[str] = mapped_column(String(20), nullable=False, default="seeds")

    # Meaning per type:
    #   seeds       → N seeds to add
    #   free_install→ N free installs to grant
    #   discount    → N % discount on next install
    value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    uses_count: Mapped[int] = mapped_column(Integer, default=0)
    per_user_limit: Mapped[int] = mapped_column(Integer, default=1)
    min_seeds: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    uses: Mapped[list["CouponUse"]] = relationship("CouponUse", back_populates="coupon")

    def __repr__(self) -> str:
        return f"<Coupon code={self.code} type={self.type} value={self.value}>"


class CouponUse(Base):
    __tablename__ = "coupon_uses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    coupon_id: Mapped[int] = mapped_column(Integer, ForeignKey("coupons.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    used_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    coupon: Mapped["Coupon"] = relationship("Coupon", back_populates="uses")
    user: Mapped["User"] = relationship("User", back_populates="coupon_uses")

    def __repr__(self) -> str:
        return f"<CouponUse coupon={self.coupon_id} user={self.user_id}>"
