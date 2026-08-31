"""
Database models for LossGraph

Implements the core entities: Transaction, Customer, Entity, Relationship, RiskEvent
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Enum, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class TransactionStatus(str, enum.Enum):
    """Transaction status enum"""
    APPROVED = "approved"
    DECLINED = "declined"
    PENDING = "pending"
    FLAGGED = "flagged"
    HELD = "held"


class EventType(str, enum.Enum):
    """Risk event type enum"""
    COORDINATED_RETURN = "coordinated_return"
    FRAUD_SPIKE = "fraud_spike"
    CHARGEBACK_WAVE = "chargeback_wave"
    CARD_ABUSE = "card_abuse"
    REFUND_ABUSE = "refund_abuse"
    UNUSUAL_BEHAVIOR = "unusual_behavior"


class EventStatus(str, enum.Enum):
    """Risk event status enum"""
    DETECTED = "detected"
    INVESTIGATING = "investigating"
    CONFIRMED = "confirmed"
    DISMISSED = "dismissed"
    ACTIONED = "actioned"
    RESOLVED = "resolved"


class ActionType(str, enum.Enum):
    """Intervention action type enum"""
    ALLOW = "allow"
    MONITOR = "monitor"
    VERIFY = "verify"
    HOLD = "hold"
    BLOCK = "block"
    INVESTIGATE_CLUSTER = "investigate_cluster"


class Merchant(Base):
    """Merchant entity"""
    __tablename__ = "merchants"
    
    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(String, unique=True, index=True)
    name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    risk_tolerance = Column(String, default="moderate")  # conservative, moderate, aggressive
    false_positive_cost = Column(Float, default=500.0)  # Cost per false positive
    verification_cost = Column(Float, default=40.0)
    
    # Relationships
    transactions = relationship("Transaction", back_populates="merchant")
    risk_events = relationship("RiskEvent", back_populates="merchant")


class Customer(Base):
    """Customer entity"""
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(String, unique=True, index=True)
    merchant_id = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    transaction_count = Column(Integer, default=0)
    return_count = Column(Integer, default=0)
    refund_count = Column(Integer, default=0)
    chargeback_count = Column(Integer, default=0)
    lifetime_value = Column(Float, default=0.0)
    risk_score = Column(Float, default=0.0)
    
    # Relationships
    transactions = relationship("Transaction", back_populates="customer")
    entities = relationship("Entity", back_populates="associated_customer")


class Transaction(Base):
    """Transaction entity"""
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String, unique=True, index=True)
    merchant_id = Column(String, ForeignKey("merchants.merchant_id"))
    customer_id = Column(String, ForeignKey("customers.customer_id"))
    amount = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    payment_method = Column(String)
    device_id = Column(String, index=True)
    address_id = Column(String, index=True)
    product_ids = Column(JSON, default=[])
    status = Column(Enum(TransactionStatus), default=TransactionStatus.APPROVED)
    risk_score = Column(Float, default=0.0)
    expected_loss = Column(Float, default=0.0)
    
    # Relationships
    merchant = relationship("Merchant", back_populates="transactions")
    customer = relationship("Customer", back_populates="transactions")
    related_events = relationship("RiskEvent", secondary="risk_event_transaction", back_populates="transactions")


class Entity(Base):
    """Generic entity (device, address, payment fingerprint, etc.)"""
    __tablename__ = "entities"
    
    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(String, index=True)
    entity_type = Column(String, index=True)  # device, address, payment_fingerprint, product
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    risk_score = Column(Float, default=0.0)
    associated_customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    merchant_id = Column(String, index=True)
    metadata = Column(JSON, default={})
    
    # Relationships
    associated_customer = relationship("Customer", back_populates="entities")
    source_relationships = relationship("Relationship", foreign_keys="Relationship.source_id", back_populates="source")
    target_relationships = relationship("Relationship", foreign_keys="Relationship.target_id", back_populates="target")


class Relationship(Base):
    """Relationship between entities in the risk graph"""
    __tablename__ = "relationships"
    
    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("entities.id"))
    target_id = Column(Integer, ForeignKey("entities.id"))
    relationship_type = Column(String)  # shared_device, shared_address, shared_payment, etc.
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    frequency = Column(Integer, default=1)
    confidence = Column(Float, default=0.5)
    merchant_id = Column(String, index=True)
    
    # Relationships
    source = relationship("Entity", foreign_keys=[source_id], back_populates="source_relationships")
    target = relationship("Entity", foreign_keys=[target_id], back_populates="target_relationships")


class RiskEvent(Base):
    """Risk event detection and tracking"""
    __tablename__ = "risk_events"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, unique=True, index=True)
    merchant_id = Column(String, ForeignKey("merchants.merchant_id"), index=True)
    event_type = Column(Enum(EventType))
    start_time = Column(DateTime, default=datetime.utcnow)
    detection_time = Column(DateTime, default=datetime.utcnow, index=True)
    exposure = Column(Float, default=0.0)
    confidence = Column(Float, default=0.0)
    status = Column(Enum(EventStatus), default=EventStatus.DETECTED, index=True)
    affected_entity_count = Column(Integer, default=0)
    affected_transaction_count = Column(Integer, default=0)
    evidence = Column(JSON, default={})
    recommended_action = Column(Enum(ActionType), default=ActionType.MONITOR)
    root_cause = Column(Text)
    timeline = Column(JSON, default=[])
    
    # Relationships
    merchant = relationship("Merchant", back_populates="risk_events")
    transactions = relationship("Transaction", secondary="risk_event_transaction", back_populates="related_events")
    counterfactuals = relationship("Counterfactual", back_populates="risk_event")


class Counterfactual(Base):
    """Counterfactual intervention simulation"""
    __tablename__ = "counterfactuals"
    
    id = Column(Integer, primary_key=True, index=True)
    risk_event_id = Column(Integer, ForeignKey("risk_events.id"))
    action = Column(Enum(ActionType))
    expected_loss = Column(Float)
    loss_prevented = Column(Float)
    legitimate_orders_affected = Column(Integer, default=0)
    operational_cost = Column(Float, default=0.0)
    net_benefit = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    risk_event = relationship("RiskEvent", back_populates="counterfactuals")


# Association table for many-to-many relationship between RiskEvent and Transaction
from sqlalchemy import Table
risk_event_transaction = Table(
    'risk_event_transaction',
    Base.metadata,
    Column('risk_event_id', Integer, ForeignKey('risk_events.id')),
    Column('transaction_id', Integer, ForeignKey('transactions.id'))
)
