from odoo import api, models

class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def create(self, vals):
        user = super().create(vals)

        # Detecta se foi criado como portal
        portal_group = self.env.ref("base.group_portal")
        internal_group = self.env.ref("base.group_user")

        if portal_group in user.groups_id and internal_group not in user.groups_id:
            # Remove portal e adiciona interno
            user.write({
                'groups_id': [(3, portal_group.id), (4, internal_group.id)]
            })

        return user
