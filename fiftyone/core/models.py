"""
FiftyOne models.

| Copyright 2017-2020, Voxel51, Inc.
| `voxel51.com <https://voxel51.com/>`_
|
"""
import logging
import numpy as np

import eta.core.image as etai
import eta.core.learning as etal
import eta.core.models as etam
import eta.core.utils as etau
import eta.core.video as etav
import eta.core.web as etaw

import fiftyone as fo
import fiftyone.core.labels as fol
import fiftyone.core.media as fom
import fiftyone.core.utils as fou
import fiftyone.core.validation as fov

foe = fou.lazy_import("fiftyone.core.eta_utils")
fout = fou.lazy_import("fiftyone.utils.torch")


logger = logging.getLogger(__name__)


def apply_model(
    samples, model, label_field, confidence_thresh=None, batch_size=None
):
    """Applies the given :class:`Model` to the samples in the collection.

    Args:
        samples: a :class:`fiftyone.core.collections.SampleCollection`
        model: a :class:`Model`
        label_field: the name (or prefix) of the field in which to store the
            model predictions
        confidence_thresh (None): an optional confidence threshold to apply to
            any applicable labels generated by the model
        batch_size (None): an optional batch size to use. Only applicable for
            image samples
    """
    if samples.media_type == fom.VIDEO:
        return _apply_video_model(
            samples, model, label_field, confidence_thresh
        )

    # Use data loaders for Torch models, if possible
    if isinstance(model, TorchModelMixin):
        return fout.apply_torch_image_model(
            samples,
            model,
            label_field,
            confidence_thresh=confidence_thresh,
            batch_size=batch_size,
        )

    batch_size = _parse_batch_size(batch_size, model)

    if batch_size is not None:
        return _apply_image_model_batch(
            samples, model, label_field, confidence_thresh, batch_size
        )

    return _apply_image_model_single(
        samples, model, label_field, confidence_thresh
    )


def _apply_image_model_single(samples, model, label_field, confidence_thresh):
    with model:
        with fou.ProgressBar() as pb:
            for sample in pb(samples):
                # @todo use DataLoader-like strategy to improve performance?
                img = etai.read(sample.filepath)
                label = model.predict(img)

                sample.add_labels(
                    label, label_field, confidence_thresh=confidence_thresh
                )


def _apply_image_model_batch(
    samples, model, label_field, confidence_thresh, batch_size
):
    samples_loader = fou.iter_batches(samples, batch_size)

    with model:
        with fou.ProgressBar(samples) as pb:
            for sample_batch in samples_loader:
                # @todo use DataLoader-like strategy to improve performance?
                imgs = [etai.read(sample.filepath) for sample in sample_batch]
                label_batch = model.predict_all(imgs)

                for sample, label in zip(sample_batch, label_batch):
                    sample.add_labels(
                        label, label_field, confidence_thresh=confidence_thresh
                    )

                pb.set_iteration(pb.iteration + len(imgs))


def _apply_video_model(samples, model, label_field, confidence_thresh):
    with model:
        with fou.ProgressBar() as pb:
            for sample in pb(samples):
                with etav.FFmpegVideoReader(sample.filepath) as video_reader:
                    label = model.predict(video_reader)

                # Save labels
                sample.add_labels(
                    label, label_field, confidence_thresh=confidence_thresh
                )


def compute_embeddings(samples, model, embeddings_field=None, batch_size=None):
    """Computes embeddings for the samples in the collection using the given
    :class:`Model`.

    If an ``embeddings_field`` is provided, the embeddings are saved to the
    samples; otherwise, the embeddings are returned in-memory.

    The :class:`Model` must implement the :class:`EmbeddingsMixin` mixin.

    Args:
        samples: a :class:`fiftyone.core.collections.SampleCollection`
        model: a :class:`Model` that implements the :class:`EmbeddingsMixin`
            mixin
        embeddings_field (None): the name of a field in which to store the
            embeddings
        batch_size (None): an optional batch size to use. Only applicable for
            image samples

    Returns:
        ``None``, if an ``embeddings_field`` is provided; otherwise, a numpy
        array whose first dimension is ``len(samples)`` containing the
        embeddings
    """
    if not isinstance(model, EmbeddingsMixin):
        raise ValueError("Model must implement the %s mixin" % EmbeddingsMixin)

    if not model.has_embeddings:
        raise ValueError(
            "Model does not expose embeddings (model.has_embeddings = %s)"
            % model.has_embeddings
        )

    if samples.media_type == fom.VIDEO:
        return _compute_video_embeddings(samples, model, embeddings_field)

    # Use data loaders for Torch models, if possible
    if isinstance(model, TorchModelMixin):
        return fout.compute_torch_image_embeddings(
            samples,
            model,
            embeddings_field=embeddings_field,
            batch_size=batch_size,
        )

    batch_size = _parse_batch_size(batch_size, model)

    if batch_size is not None:
        return _compute_image_embeddings_batch(
            samples, model, embeddings_field, batch_size
        )

    return _compute_image_embeddings_single(samples, model, embeddings_field)


def _compute_image_embeddings_single(samples, model, embeddings_field):
    embeddings = []

    with model:
        with fou.ProgressBar() as pb:
            for sample in pb(samples):
                img = etai.read(sample.filepath)
                embedding = model.embed(img)

                if embeddings_field:
                    sample[embeddings_field] = embedding[0]
                    sample.save()
                else:
                    embeddings.append(embedding)

    if embeddings_field:
        return None

    return np.concatenate(embeddings)


def _compute_image_embeddings_batch(
    samples, model, embeddings_field, batch_size
):
    samples_loader = fou.iter_batches(samples, batch_size)

    embeddings = []

    with model:
        with fou.ProgressBar(samples) as pb:
            for sample_batch in samples_loader:
                imgs = [etai.read(sample.filepath) for sample in sample_batch]
                embeddings_batch = model.embed_all(imgs)

                if embeddings_field:
                    for sample, embedding in zip(
                        sample_batch, embeddings_batch
                    ):
                        sample[embeddings_field] = embedding
                        sample.save()
                else:
                    embeddings.append(embeddings_batch)

                pb.set_iteration(pb.iteration + len(imgs))

    if embeddings_field:
        return None

    return np.concatenate(embeddings)


def _compute_video_embeddings(samples, model, embeddings_field):
    embeddings = []

    with model:
        with fou.ProgressBar() as pb:
            for sample in pb(samples):
                with etav.FFmpegVideoReader(sample.filepath) as video_reader:
                    embedding = model.embed(video_reader)

                if embeddings_field:
                    sample[embeddings_field] = embedding[0]
                    sample.save()
                else:
                    embeddings.append(embedding)

    if embeddings_field:
        return None

    return np.concatenate(embeddings)


def compute_patch_embeddings(
    samples,
    model,
    patches_field,
    embeddings_field=None,
    batch_size=None,
    force_square=False,
    alpha=None,
):
    """Computes embeddings for the image patches defined by ``patches_field``
    of the samples in the collection using the given :class:`Model`.

    If an ``embeddings_field`` is provided, the embeddings are saved to the
    samples; otherwise, the embeddings are returned in-memory.

    The :class:`Model` must implement the :class:`EmbeddingsMixin` mixin.

    Args:
        samples: a :class:`fiftyone.core.collections.SampleCollection`
        model: a :class:`Model` that implements the :class:`EmbeddingsMixin`
            mixin
        patches_field: a :class:`fiftyone.core.labels.Detection`,
            :class:`fiftyone.core.labels.Detections`,
            :class:`fiftyone.core.labels.Polyline`, or
            :class:`fiftyone.core.labels.Polylines` field defining the image
            patches in each sample to embed
        embeddings_field (None): the name of a field in which to store the
            embeddings
        batch_size (None): an optional batch size to use
        force_square (False): whether to minimally manipulate the patch
            bounding boxes into squares prior to extraction
        alpha (None): an optional expansion/contraction to apply to the patches
            before extracting them, in ``[-1, \infty)``. If provided, the
            length and width of the box are expanded (or contracted, when
            ``alpha < 0``) by ``(100 * alpha)%``. For example, set
            ``alpha = 1.1`` to expand the boxes by 10%, and set ``alpha = 0.9``
            to contract the boxes by 10%

    Returns:
        ``None``, if an ``embeddings_field`` is provided; otherwise, a dict
        mapping sample IDs to arrays of patch embeddings
    """
    if samples.media_type != fom.IMAGE:
        raise ValueError("This method only supports image samples")

    if not isinstance(model, EmbeddingsMixin):
        raise ValueError("Model must implement the %s mixin" % EmbeddingsMixin)

    if not model.has_embeddings:
        raise ValueError(
            "Model does not expose embeddings (model.has_embeddings = %s)"
            % model.has_embeddings
        )

    # Use data loaders for Torch models, if possible
    if isinstance(model, TorchModelMixin):
        return fout.compute_torch_image_patch_embeddings(
            samples,
            model,
            patches_field,
            embeddings_field=embeddings_field,
            batch_size=batch_size,
        )

    allowed_types = (
        fol.Detection,
        fol.Detections,
        fol.Polyline,
        fol.Polylines,
    )
    fov.validate_collection_label_fields(samples, patches_field, allowed_types)

    batch_size = _parse_batch_size(batch_size, model)

    embeddings_dict = {}

    with model:
        with fou.ProgressBar() as pb:
            for sample in pb(samples):
                detections = _parse_patches(sample, patches_field)
                if detections is None or not detections.detections:
                    continue

                img = etai.read(sample.filepath)

                if batch_size is None:
                    embeddings = _embed_patches_single(
                        model, img, detections, force_square, alpha
                    )
                else:
                    embeddings = _embed_patches_batch(
                        model, img, detections, force_square, alpha, batch_size
                    )

                if embeddings_field:
                    sample[embeddings_field] = embeddings
                    sample.save()
                else:
                    embeddings_dict[sample.id] = embeddings

    return embeddings_dict if not embeddings_field else None


def _embed_patches_single(model, img, detections, force_square, alpha):
    embeddings = []
    for detection in detections.detections:
        patch = _extract_patch(img, detection, force_square, alpha)
        embedding = model.embed(patch)
        embeddings.append(embedding)

    return np.concatenate(embeddings)


def _embed_patches_batch(
    model, img, detections, force_square, alpha, batch_size
):
    embeddings = []
    for detection_batch in fou.iter_batches(detections.detections, batch_size):
        patches = [
            _extract_patch(img, d, force_square, alpha)
            for d in detection_batch
        ]
        embeddings_batch = model.embed_all(patches)
        embeddings.append(embeddings_batch)

    return np.concatenate(embeddings)


def _parse_patches(sample, patches_field):
    label = sample[patches_field]

    if isinstance(label, fol.Detections):
        return label

    if isinstance(label, fol.Detection):
        return fol.Detections(detections=[label])

    if isinstance(label, fol.Polyline):
        return fol.Detections(detections=[label.to_detection()])

    if isinstance(label, fol.Polylines):
        return label.to_detections()

    return None


def _extract_patch(img, detection, force_square, alpha):
    dobj = detection.to_detected_object()

    bbox = dobj.bounding_box
    if alpha is not None:
        bbox = bbox.pad_relative(alpha)

    return bbox.extract_from(img, force_square=force_square)


def _parse_batch_size(batch_size, model):
    if batch_size is None:
        batch_size = fo.config.default_batch_size

    if batch_size is not None and batch_size > 1 and model.ragged_batches:
        logger.warning("Model does not support batching")
        batch_size = None

    return batch_size


def load_model(model_config_dict, model_path=None, **kwargs):
    """Loads the model specified by the given :class:`ModelConfig` dict.

    Args:
        model_config_dict: a :class:`ModelConfig` dict
        model_path (None): an optional model path to inject into the
            ``model_path`` field of the model's ``Config`` instance, which must
            implement the ``eta.core.learning.HasPublishedModel`` interface.
            This is useful when working with a model whose weights are stored
            locally and do not need to be downloaded
        **kwargs: optional keyword arguments to inject into the model's
            ``Config`` instance

    Returns:
        a :class:`Model` instance
    """
    # Inject config args
    if kwargs:
        if model_config_dict["type"] == etau.get_class_name(foe.ETAModel):
            _merge_config(model_config_dict["config"]["config"], kwargs)
        else:
            _merge_config(model_config_dict["config"], kwargs)

    # Load model config
    config = ModelConfig.from_dict(model_config_dict)

    #
    # Inject model path
    #
    # Models must be implemented in one of the following ways in order for
    # us to know how to inject ``model_path``:
    #
    # (1) Their config implements ``eta.core.learning.HasPublishedModel``
    #
    # (2) Their config is an ``fiftyone.core.eta_utils.ETAModelConfig`` whose
    #     embedded config implements ``eta.core.learning.HasPublishedModel``
    #
    if model_path:
        if isinstance(config.config, etal.HasPublishedModel):
            config.config.model_name = None
            config.config.model_path = model_path
        elif isinstance(config.config, foe.ETAModelConfig) and isinstance(
            config.config.config, etal.HasPublishedModel
        ):
            config.config.config.model_name = None
            config.config.config.model_path = model_path
        else:
            raise ValueError(
                "Model config must implement the %s interface"
                % etal.HasPublishedModel
            )

    # Build model
    return config.build()


def _merge_config(d, kwargs):
    for k, v in kwargs.items():
        if k in d and isinstance(d[k], dict):
            d[k].update(v)
        else:
            d[k] = v


class ModelConfig(etal.ModelConfig):
    """Base configuration class that encapsulates the name of a :class:`Model`
    and an instance of its associated Config class.

    Args:
        type: the fully-qualified class name of the :class:`Model` subclass
        config: an instance of the Config class associated with the model
    """

    pass


class Model(etal.Model):
    """Abstract base class for models.

    This class declares the following conventions:

    (a)     :meth:`Model.__init__` should take a single ``config`` argument
            that is an instance of ``<Model>Config``

    (b)     Models implement the context manager interface. This means that
            models can optionally use context to perform any necessary setup
            and teardown, and so any code that builds a model should use the
            ``with`` syntax
    """

    @property
    def ragged_batches(self):
        """True/False whether :meth:`transforms` may return tensors of
        different sizes and therefore passing ragged lists of data to
        :meth:`predict_all` is not allowed.
        """
        raise NotImplementedError("subclasses must implement ragged_batches")

    @property
    def transforms(self):
        """The preprocessing function that will/must be applied to each input
        before prediction, or ``None`` if no preprocessing is performed.
        """
        raise NotImplementedError("subclasses must implement transforms")

    def predict(self, arg):
        """Peforms prediction on the given data.

        Image models should support, at minimum, processing ``arg`` values that
        are uint8 numpy arrays (HWC).

        Video models should support, at minimum, processing ``arg`` values that
        are ``eta.core.video.VideoReader`` instances.

        Args:
            arg: the data

        Returns:
            a :class:`fiftyone.core.labels.Label` instance or dict of
            :class:`fiftyone.core.labels.Label` instances containing the
            predictions
        """
        raise NotImplementedError("subclasses must implement predict()")

    def predict_all(self, args):
        """Performs prediction on the given iterable of data.

        Image models should support, at minimum, processing ``args`` values
        that are either lists of uint8 numpy arrays (HWC) or numpy array
        tensors (NHWC).

        Video models should support, at minimum, processing ``args`` values
        that are lists of ``eta.core.video.VideoReader`` instances.

        Subclasses can override this method to increase efficiency, but, by
        default, this method simply iterates over the data and applies
        :meth:`predict` to each.

        Args:
            args: an iterable of data

        Returns:
            a list of :class:`fiftyone.core.labels.Label` instances or a list
            of dicts of :class:`fiftyone.core.labels.Label` instances
            containing the predictions
        """
        return [self.predict(arg) for arg in args]


class EmbeddingsMixin(object):
    """Mixin for :class:`Model` classes that can generate embeddings for
    their predictions.

    This mixin allows for the possibility that only some instances of a class
    are capable of generating embeddings, per the value of the
    :meth:`has_embeddings` property.
    """

    @property
    def has_embeddings(self):
        """Whether this instance has embeddings."""
        raise NotImplementedError("subclasses must implement has_embeddings")

    def get_embeddings(self):
        """Returns the embeddings generated by the last forward pass of the
        model.

        By convention, this method should always return an array whose first
        axis represents batch size (which will always be 1 when :meth:`predict`
        was last used).

        Returns:
            a numpy array containing the embedding(s)
        """
        raise NotImplementedError("subclasses must implement get_embeddings()")

    def embed(self, arg):
        """Generates an embedding for the given data.

        Subclasses can override this method to increase efficiency, but, by
        default, this method simply calls :meth:`predict` and then returns
        :meth:`get_embeddings`.

        Args:
            arg: the data. See :meth:`predict` for details

        Returns:
            a numpy array containing the embedding
        """
        # pylint: disable=no-member
        self.predict(arg)
        return self.get_embeddings()

    def embed_all(self, args):
        """Generates embeddings for the given iterable of data.

        Subclasses can override this method to increase efficiency, but, by
        default, this method simply iterates over the data and applies
        :meth:`embed` to each.

        Args:
            args: an iterable of data. See :meth:`predict_all` for details

        Returns:
            a numpy array containing the embeddings stacked along axis 0
        """
        return np.stack([self.embed(arg) for arg in args], axis=0)


class TorchModelMixin(object):
    """Mixin for :class:`Model` classes that support feeding data for inference
    via a ``torch.utils.data.DataLoader``.
    """

    pass


class ModelManagerConfig(etam.ModelManagerConfig):
    """Config settings for a :class:`ModelManager`.

    Args:
        url (None): the URL of the file
        google_drive_id (None): the ID of the file in Google Drive
        extract_archive (None): whether to extract the downloaded model, which
            is assumed to be an archive
        delete_archive (None): whether to delete the archive after extracting
            it, if applicable
    """

    def __init__(self, d):
        super().__init__(d)

        self.url = self.parse_string(d, "url", default=None)
        self.google_drive_id = self.parse_string(
            d, "google_drive_id", default=None
        )


class ModelManager(etam.ModelManager):
    """Class for downloading public FiftyOne models."""

    @staticmethod
    def upload_model(model_path, *args, **kwargs):
        raise NotImplementedError("Uploading models via API is not supported")

    def _download_model(self, model_path):
        if self.config.google_drive_id:
            gid = self.config.google_drive_id
            logger.info("Downloading model from Google Drive ID '%s'...", gid)
            etaw.download_google_drive_file(gid, path=model_path)
        elif self.config.url:
            url = self.config.url
            logger.info("Downloading model from '%s'...", url)
            etaw.download_file(url, path=model_path)
        else:
            raise ValueError(
                "Invalid ModelManagerConfig '%s'" % str(self.config)
            )

    def delete_model(self):
        raise NotImplementedError("Deleting models via API is not supported")
