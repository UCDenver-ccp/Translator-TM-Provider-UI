import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import models


class ModelTestCase(unittest.TestCase):

    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        session = sessionmaker()
        session.configure(bind=self.engine)
        self.session = session()
        models.Model.metadata.create_all(self.engine)
        self.populate_db()

    def populate_db(self):
        self.assertion = models.Assertion('abcde', 'CHEBI:24433', 'PR:000000015', 'biolink:ChemicalToGeneAssociation')
        self.assertion.id = 1
        self.session.add(self.assertion)
        self.evidence = models.Evidence('xyz', 'abcde', 'PMID:32807176', 'something', 'def', 'efd', 'title', 'article', 2020)
        self.session.add(self.evidence)
        self.subject_entity = models.Entity('def', '1|2', 'a')
        self.session.add(self.subject_entity)
        self.object_entity = models.Entity('efd', '2|4', 'be')
        self.session.add(self.object_entity)
        self.evaluation = models.Evaluation('abcde', False, False, False, False, 1234)
        self.session.add(self.evaluation)
        self.evidence_score_1 = models.EvidenceScore('xyz', 'biolink:entity_negatively_regulates_entity', 0.000161453)
        self.session.add(self.evidence_score_1)
        self.evidence_score_2 = models.EvidenceScore('xyz', 'biolink:entity_positively_regulates_entity', 0.999207900)
        self.session.add(self.evidence_score_2)
        self.evidence_score_3 = models.EvidenceScore('xyz', 'false', 0.000630744)
        self.session.add(self.evidence_score_3)
        self.pr_to_uniprot = models.PRtoUniProt('PR:000000015', 'UniProtKB:P19883')
        self.session.add(self.pr_to_uniprot)
        self.session.commit()

    def tearDown(self):
        models.Model.metadata.drop_all(self.engine)

# Query Tests

    def test_query_assertion(self):
        expected = [self.assertion]
        result = self.session.query(models.Assertion).all()
        self.assertEqual(result, expected)

    def test_query_evidence(self):
        expected = [self.evidence]
        result = self.session.query(models.Evidence).all()
        self.assertEqual(result, expected)

    def test_query_entity(self):
        expected = [self.subject_entity, self.object_entity]
        result = self.session.query(models.Entity).all()
        self.assertEqual(result, expected)

    def test_query_evaluation(self):
        expected = [self.evaluation]
        result = self.session.query(models.Evaluation).all()
        self.assertEqual(result, expected)

    def test_query_evidence_score(self):
        expected = [self.evidence_score_1, self.evidence_score_2, self.evidence_score_3]
        result = self.session.query(models.EvidenceScore).all()
        self.assertEqual(result, expected)

    def test_query_pr_to_uniprot(self):
        expected = [self.pr_to_uniprot]
        result = self.session.query(models.PRtoUniProt).all()
        self.assertEqual(result, expected)

# Relationship Tests

    def test_relationship_assertion_to_evidence(self):
        expected = [self.evidence]
        assertion_record = self.session.query(models.Assertion).one()
        self.assertEqual(assertion_record.evidence_list, expected)

    def test_relationship_assertion_to_pr_to_uniprot(self):
        assertion_record = self.session.query(models.Assertion).one()
        self.assertIsNone(assertion_record.subject_uniprot)
        self.assertEqual(assertion_record.object_uniprot, self.pr_to_uniprot)

    def test_relationship_evidence_to_assertion(self):
        evidence_record = self.session.query(models.Evidence).one()
        self.assertEqual(evidence_record.assertion, self.assertion)

    def test_relationship_evidence_to_entity(self):
        evidence_record = self.session.query(models.Evidence).one()
        self.assertEqual(evidence_record.subject_entity, self.subject_entity)
        self.assertEqual(evidence_record.object_entity, self.object_entity)

    def test_relationship_evidence_to_evidence_score(self):
        expected = [self.evidence_score_1, self.evidence_score_2, self.evidence_score_3]
        evidence_record = self.session.query(models.Evidence).one()
        self.assertEqual(evidence_record.evidence_scores, expected)

# Method Tests

    def test_method_assertion_get_predicate_scores(self):
        expected = {'biolink:entity_positively_regulates_entity': 0.999207900}
        assertion_record = self.session.query(models.Assertion).one()
        self.assertEqual(assertion_record.get_predicate_scores(), expected)

    def test_method_assertion_get_predicates(self):
        expected = {'biolink:entity_positively_regulates_entity'}
        assertion_record = self.session.query(models.Assertion).one()
        self.assertEqual(assertion_record.get_predicates(), expected)

    def test_method_assertion_get_aggregate_score(self):
        assertion_record = self.session.query(models.Assertion).one()
        self.assertEqual(assertion_record.get_aggregate_score('biolink:entity_positively_regulates_entity'), 0.999207900)

    def test_method_evidence_get_top_predicate(self):
        evidence_record = self.session.query(models.Evidence).one()
        self.assertEqual(evidence_record.get_top_predicate(), 'biolink:entity_positively_regulates_entity')

    def test_method_evidence_get_predicates(self):
        expected = {'false', 'biolink:entity_negatively_regulates_entity', 'biolink:entity_positively_regulates_entity'}
        evidence_record = self.session.query(models.Evidence).one()
        self.assertEqual(evidence_record.get_predicates(), expected)

    def test_method_evidence_get_score(self):
        evidence_record = self.session.query(models.Evidence).one()
        self.assertEqual(evidence_record.get_score(), 0.999207900)
        self.assertEqual(evidence_record.get_score('false'), 0.000630744)
        self.assertEqual(evidence_record.get_score('biolink:entity_negatively_regulates_entity'), 0.000161453)
        self.assertEqual(evidence_record.get_score('biolink:entity_positively_regulates_entity'), 0.999207900)
