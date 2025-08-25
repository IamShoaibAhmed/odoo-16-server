/** @odoo-module **/

import { PaymentMethod } from "@point_of_sale/app/store/models";
import { registerModel } from "@point_of_sale/app/store/model_registries";

registerModel({
    modelClass: PaymentMethod,
    fields: {
        bank_fee_type: { type: "string" },
        bank_fee_value: { type: "float" },
    },
});
