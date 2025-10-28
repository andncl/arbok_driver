from sqlalchemy import (
    BigInteger,
    Boolean,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

class Base(DeclarativeBase):
    pass

class SqlRun(Base):
    __tablename__ = "runs"

    ### Run metadata
    run_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(
        UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    exp_id: Mapped[int] = mapped_column(ForeignKey("experiments.exp_id"))
    name: Mapped[str] = mapped_column(String)
    device: Mapped[str] = mapped_column(String)
    sub_device: Mapped[str] = mapped_column(String)
    setup: Mapped[str] = mapped_column(String)

    ### Data specific to this run
    result_counter: Mapped[int] = mapped_column(Integer, default=0)
    batch_counter: Mapped[int] = mapped_column(Integer, default=0)
    coords: Mapped[list[str]] = mapped_column(ARRAY(String))
    sweeps: Mapped[dict[int, list[str]]] = mapped_column(JSONB)

    ### Timestamps and status
    start_time: Mapped[int] = mapped_column(BigInteger)
    completed_time: Mapped[int] = mapped_column(BigInteger, default=None)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)

    measurement_exception: Mapped[str] = mapped_column(Text, default=None)
    parent_datasets: Mapped[list[int]] = mapped_column(
        ARRAY(Integer), default = None)


class SqlExperiment(Base):
    __tablename__ = "experiments"

    exp_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    creation_time: Mapped[int] = mapped_column(BigInteger)
    run_counter: Mapped[int] = mapped_column(Integer)
    format_string: Mapped[str] = mapped_column(String)

    __table_args__ = (
        UniqueConstraint("name", name="uq_experiment_name"),
    )

    def __repr__(self) -> str:
        return (f"<Experiment(exp_id={self.exp_id}, name='{self.name}', "
                f"creation_time={self.creation_time}, run_counter={self.run_counter}, "
                f"format_string='{self.format_string}')>")
