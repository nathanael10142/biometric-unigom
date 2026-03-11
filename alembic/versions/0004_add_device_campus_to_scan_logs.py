from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.add_column('scan_logs', sa.Column('device_id', sa.String(50), nullable=False, server_default='UNKNOWN'))
    op.add_column('scan_logs', sa.Column('campus_id', sa.String(50), nullable=False, server_default='UNKNOWN'))
    
    op.drop_constraint('uq_scan_agent_time', 'scan_logs', type_='unique')
    op.create_unique_constraint('uq_serial_no', 'scan_logs', ['serial_no'])
    
    op.create_index('ix_scan_device_id', 'scan_logs', ['device_id'])
    op.create_index('ix_scan_campus_id', 'scan_logs', ['campus_id'])


def downgrade() -> None:
    op.drop_index('ix_scan_campus_id', 'scan_logs')
    op.drop_index('ix_scan_device_id', 'scan_logs')
    
    op.drop_constraint('uq_serial_no', 'scan_logs', type_='unique')
    op.create_unique_constraint('uq_scan_agent_time', 'scan_logs', ['agent_uuid', 'scanned_at'])
    
    op.drop_column('scan_logs', 'campus_id')
    op.drop_column('scan_logs', 'device_id')
