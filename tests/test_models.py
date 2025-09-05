from models.receipt import Receipt, TaxLine, PaymentMethod


class TestReceiptModel:
    def test_tax_line_creation(self):
        tax_line = TaxLine(
            label="A",
            rate=10.0,
            base_amount=100.0,
            tax_amount=10.0,
            total_amount=110.0
        )
        assert tax_line.label == "A"
        assert tax_line.rate == 10.0
        assert tax_line.base_amount == 100.0
        assert tax_line.tax_amount == 10.0
        assert tax_line.total_amount == 110.0

    def test_tax_line_coherence_valid(self):
        tax_line = TaxLine(
            rate=10.0,
            base_amount=100.0,
            tax_amount=10.0,
            total_amount=110.0
        )
        assert tax_line.is_coherent() is True

    def test_tax_line_coherence_invalid(self):
        tax_line = TaxLine(
            rate=10.0,
            base_amount=100.0,
            tax_amount=15.0,
            total_amount=115.0
        )
        assert tax_line.is_coherent() is False

    def test_tax_line_auto_calculate_total(self):
        tax_line = TaxLine(
            rate=20.0,
            base_amount=50.0,
            tax_amount=10.0
        )
        assert tax_line.total_amount == 60.0

    def test_receipt_creation_minimal(self):
        receipt = Receipt(
            vendor_name="Test Shop",
            total_amount=100.0
        )
        assert receipt.vendor_name == "Test Shop"
        assert receipt.total_amount == 100.0
        assert receipt.confidence_score >= 0

    def test_receipt_creation_complete(self):
        tax_lines = [
            TaxLine(rate=10, base_amount=90, tax_amount=9, total_amount=99),
            TaxLine(rate=20, base_amount=80, tax_amount=16, total_amount=96)
        ]
        receipt = Receipt(
            vendor_name="Test Shop",
            vendor_address="123 Test St",
            vendor_siret="12345678900012",
            receipt_number="R2024001",
            date="2024-03-15",
            time="14:30",
            subtotal=170.0,
            tax_amount=25.0,
            total_amount=195.0,
            tax_lines=tax_lines,
            payment_method=PaymentMethod.CARD
        )
        assert receipt.vendor_name == "Test Shop"
        assert len(receipt.tax_lines) == 2
        assert receipt.subtotal == 170.0
        assert receipt.tax_amount == 25.0
        assert receipt.total_amount == 195.0

    def test_receipt_validation_coherent(self):
        receipt = Receipt(
            vendor_name="Test Shop",
            subtotal=100.0,
            tax_amount=10.0,
            total_amount=110.0
        )
        assert len(receipt.validation_errors) == 0
        assert receipt.confidence_score > 0.5

    def test_receipt_validation_incoherent(self):
        receipt = Receipt(
            vendor_name="Test Shop",
            subtotal=100.0,
            tax_amount=10.0,
            total_amount=120.0
        )
        assert len(receipt.validation_errors) > 0
        assert any("Amount mismatch" in err for err in receipt.validation_errors)

    def test_receipt_missing_vendor(self):
        receipt = Receipt(
            total_amount=100.0
        )
        assert "Missing vendor name" in receipt.validation_errors

    def test_receipt_date_normalization(self):
        receipt = Receipt(
            vendor_name="Test",
            date="15/03/2024",
            total_amount=100.0
        )
        assert receipt.date == "2024-03-15"

    def test_receipt_payment_normalization(self):
        test_cases = [
            ("CB", PaymentMethod.CARD),
            ("carte", PaymentMethod.CARD),
            ("espèces", PaymentMethod.CASH),
            ("cash", PaymentMethod.CASH),
            ("apple pay", PaymentMethod.MOBILE),
            ("unknown", PaymentMethod.OTHER)
        ]
        for input_val, expected in test_cases:
            receipt = Receipt(
                vendor_name="Test",
                total_amount=100,
                payment_method=input_val
            )
            assert receipt.payment_method == expected

    def test_receipt_tax_lines_calculation(self):
        tax_lines = [
            TaxLine(rate=10, base_amount=50, tax_amount=5),
            TaxLine(rate=20, base_amount=100, tax_amount=20)
        ]
        receipt = Receipt(
            vendor_name="Test Shop",
            tax_lines=tax_lines
        )
        assert receipt.subtotal == 150.0
        assert receipt.tax_amount == 25.0
        assert receipt.total_amount == 175.0

    def test_receipt_summary(self):
        receipt = Receipt(
            vendor_name="Test Shop",
            date="2024-03-15",
            subtotal=100.0,
            tax_amount=10.0,
            total_amount=110.0,
            tax_lines=[TaxLine(rate=10, base_amount=100, tax_amount=10)],
            payment_method=PaymentMethod.CARD
        )
        summary = receipt.to_summary()
        assert summary['vendor'] == "Test Shop"
        assert summary['date'] == "2024-03-15"
        assert summary['total_ttc'] == 110.0
        assert summary['tax_rates'] == [10.0]
        assert summary['payment'] == "card"
        assert summary['is_valid'] is True
