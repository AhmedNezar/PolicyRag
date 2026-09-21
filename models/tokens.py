from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal

class TokenPricing(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    input_per_million: Decimal = Field(ge=0, allow_inf_nan=False)
    output_per_million: Decimal = Field(ge=0, allow_inf_nan=False)
    
    def estimate(self, input_tokens: int, output_tokens: int) -> tuple[Decimal, Decimal, Decimal]:
        input_cost = (input_tokens * self.input_per_million) / Decimal("1000000")
        output_cost = (output_tokens * self.output_per_million) / Decimal("1000000")
        total_cost = input_cost + output_cost
        return input_cost, output_cost, total_cost