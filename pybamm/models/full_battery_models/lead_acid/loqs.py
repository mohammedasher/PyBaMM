#
# Lead-acid LOQS model
#
import pybamm
from .base_lead_acid_model import BaseModel


class LOQS(BaseModel):
    """Leading-Order Quasi-Static model for lead-acid, from [1]_.

    References
    ----------
    .. [1] V Sulzer, SJ Chapman, CP Please, DA Howey, and CW Monroe. Faster Lead-Acid
           Battery Simulations from Porous-Electrode Theory: II. Asymptotic Analysis.
           arXiv preprint arXiv:1902.01774, 2019.


    **Extends:** :class:`pybamm.lead_acid.BaseModel`
    """

    def __init__(self, options=None, name="LOQS model"):
        super().__init__(options, name)
        self.use_jacobian = False

        self.set_reactions()
        self.set_current_collector_submodel()
        self.set_interfacial_submodel()
        self.set_convection_submodel()
        self.set_porosity_submodel()
        self.set_negative_electrode_submodel()
        self.set_electrolyte_submodel()
        self.set_positive_electrode_submodel()
        self.set_thermal_submodel()
        self.set_side_reaction_submodels()

        self.build_model()

    def set_current_collector_submodel(self):

        if self.options["bc_options"]["dimensionality"] == 0:
            self.submodels["current collector"] = pybamm.current_collector.Uniform(
                self.param
            )
        elif self.options["bc_options"]["dimensionality"] == 1:
            self.submodels[
                "current collector"
            ] = pybamm.current_collector.surface_form.LeadingOrder(self.param)
        elif self.options["bc_options"]["dimensionality"] == 2:
            raise NotImplementedError(
                "Two-dimensional current collector submodel not implemented."
            )

    def set_porosity_submodel(self):

        self.submodels["leading-order porosity"] = pybamm.porosity.LeadingOrder(
            self.param
        )

    def set_convection_submodel(self):

        if self.options["convection"] is False:
            self.submodels["leading-order convection"] = pybamm.convection.NoConvection(
                self.param
            )
        if self.options["convection"] is True:
            self.submodels["leading-order convection"] = pybamm.convection.LeadingOrder(
                self.param
            )

    def set_interfacial_submodel(self):

        if self.options["surface form"] is False:
            self.submodels[
                "leading-order negative interface"
            ] = pybamm.interface.lead_acid.InverseButlerVolmer(self.param, "Negative")
            self.submodels[
                "leading-order positive interface"
            ] = pybamm.interface.lead_acid.InverseButlerVolmer(self.param, "Positive")
        else:
            self.submodels[
                "leading-order negative interface"
            ] = pybamm.interface.lead_acid.ButlerVolmer(self.param, "Negative")

            self.submodels[
                "leading-order positive interface"
            ] = pybamm.interface.lead_acid.ButlerVolmer(self.param, "Positive")
        self.reaction_submodels = {
            "Negative": [self.submodels["leading-order negative interface"]],
            "Positive": [self.submodels["leading-order positive interface"]],
        }

    def set_negative_electrode_submodel(self):

        self.submodels[
            "leading-order negative electrode"
        ] = pybamm.electrode.ohm.LeadingOrder(self.param, "Negative")

    def set_positive_electrode_submodel(self):

        self.submodels[
            "leading-order positive electrode"
        ] = pybamm.electrode.ohm.LeadingOrder(self.param, "Positive")

    def set_electrolyte_submodel(self):

        electrolyte = pybamm.electrolyte.stefan_maxwell
        surf_form = electrolyte.conductivity.surface_potential_form

        if self.options["surface form"] is False:
            self.submodels[
                "leading-order electrolyte conductivity"
            ] = electrolyte.conductivity.LeadingOrder(self.param)

        elif self.options["surface form"] == "differential":
            for domain in ["Negative", "Separator", "Positive"]:
                self.submodels[
                    "leading-order " + domain.lower() + " electrolyte conductivity"
                ] = surf_form.LeadingOrderDifferential(
                    self.param, domain, self.reactions
                )

        elif self.options["surface form"] == "algebraic":
            for domain in ["Negative", "Separator", "Positive"]:
                self.submodels[
                    "leading-order " + domain.lower() + " electrolyte conductivity"
                ] = surf_form.LeadingOrderAlgebraic(self.param, domain, self.reactions)

        self.submodels["electrolyte diffusion"] = electrolyte.diffusion.LeadingOrder(
            self.param, self.reactions
        )

    def set_side_reaction_submodels(self):
        if "oxygen" in self.options["side reactions"]:
            self.submodels[
                "leading-order oxygen diffusion"
            ] = pybamm.oxygen_diffusion.LeadingOrder(self.param, self.reactions)
            self.submodels[
                "leading-order positive oxygen interface"
            ] = pybamm.interface.lead_acid_oxygen.ForwardTafel(self.param, "Positive")
            self.submodels[
                "leading-order negative oxygen interface"
            ] = pybamm.interface.lead_acid_oxygen.LeadingOrderDiffusionLimited(
                self.param, "Negative"
            )
        else:
            self.submodels[
                "leading-order oxygen diffusion"
            ] = pybamm.oxygen_diffusion.NoOxygen(self.param)
            self.submodels[
                "leading-order positive oxygen interface"
            ] = pybamm.interface.lead_acid_oxygen.NoReaction(self.param, "Positive")
            self.submodels[
                "leading-order negative oxygen interface"
            ] = pybamm.interface.lead_acid_oxygen.NoReaction(self.param, "Negative")
        self.reaction_submodels["Negative"].append(
            self.submodels["leading-order negative oxygen interface"]
        )
        self.reaction_submodels["Positive"].append(
            self.submodels["leading-order positive oxygen interface"]
        )

    @property
    def default_spatial_methods(self):
        base_spatial_methods = {"macroscale": pybamm.FiniteVolume}
        if self.options["bc_options"]["dimensionality"] in [0, 1]:
            base_spatial_methods["current collector"] = pybamm.FiniteVolume
        elif self.options["bc_options"]["dimensionality"] == 2:
            base_spatial_methods["current collector"] = pybamm.ScikitFiniteElement
        return base_spatial_methods

    @property
    def default_submesh_types(self):
        base_submeshes = {
            "negative electrode": pybamm.Uniform1DSubMesh,
            "separator": pybamm.Uniform1DSubMesh,
            "positive electrode": pybamm.Uniform1DSubMesh,
        }
        if self.options["bc_options"]["dimensionality"] in [0, 1]:
            base_submeshes["current collector"] = pybamm.Uniform1DSubMesh
        elif self.options["bc_options"]["dimensionality"] == 2:
            base_submeshes["current collector"] = pybamm.Scikit2DSubMesh
        return base_submeshes

    @property
    def default_geometry(self):
        if self.options["bc_options"]["dimensionality"] == 0:
            return pybamm.Geometry("1D macro")
        elif self.options["bc_options"]["dimensionality"] == 1:
            return pybamm.Geometry("1+1D macro")
        elif self.options["bc_options"]["dimensionality"] == 2:
            return pybamm.Geometry("2+1D macro")

    @property
    def default_solver(self):
        """
        Create and return the default solver for this model
        """

        if self.options["surface form"] == "algebraic":
            return pybamm.ScikitsDaeSolver()
        else:
            return pybamm.ScipySolver()
