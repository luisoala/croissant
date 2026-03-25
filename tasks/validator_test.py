import unittest
from validator import validate_data


class TestCroissantTasksValidator(unittest.TestCase):

  def test_valid_problem(self):
    conforms, _ = validate_data("testdata/valid_problem.jsonld")
    self.assertTrue(conforms, "Valid problem should pass validation.")

  def test_invalid_problem(self):
    conforms, text = validate_data("testdata/invalid_problem.jsonld")
    self.assertFalse(conforms, "Problem with no specs should fail.")
    self.assertIn(
        "A TaskProblem must have at least one property (input, output, or implementation) that is a spec class",
        text,
    )


  def test_valid_solution(self):
    conforms, _ = validate_data("testdata/valid_solution.jsonld")
    self.assertTrue(conforms, "Valid solution should pass validation.")

  def test_invalid_solution(self):
    conforms, text = validate_data("testdata/invalid_solution.jsonld")
    self.assertFalse(conforms, "Solution without schema:isBasedOn should fail.")
    self.assertIn(
        "A TaskSolution must be formally linked to a TaskProblem via"
        " schema:isBasedOn",
        text,
    )


  def test_direct_task(self):
    conforms, _ = validate_data("testdata/direct_task.jsonld")
    self.assertTrue(conforms, "Direct Task with concrete values should pass.")

  def test_invalid_solution_with_spec(self):
    conforms, text = validate_data("testdata/invalid_solution_with_spec.jsonld")
    self.assertFalse(conforms, "Solution with spec should fail.")
    self.assertIn(
        "A TaskSolution cannot have an OutputSpec as output.",
        text,
    )


if __name__ == "__main__":
  unittest.main()

